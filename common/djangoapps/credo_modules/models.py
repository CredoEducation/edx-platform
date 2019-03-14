import logging
import time
import datetime
import json
import re
import uuid
from urlparse import urlparse
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.db import models, IntegrityError, OperationalError, transaction
from django.db.models import F, Value
from django.db.models.functions import Concat
from opaque_keys.edx.django.models import CourseKeyField
from opaque_keys.edx.keys import CourseKey, UsageKey
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.utils.timezone import utc

from credo_modules.utils import additional_profile_fields_hash
from student.models import CourseEnrollment, ENROLL_STATUS_CHANGE, EnrollStatusChange


log = logging.getLogger("course_usage")


class CredoModulesUserProfile(models.Model):
    """
    This table contains info about the credo modules student.
    """
    class Meta(object):
        db_table = "credo_modules_userprofile"
        ordering = ('user', 'course_id')
        unique_together = (('user', 'course_id'),)

    user = models.ForeignKey(User)
    course_id = CourseKeyField(max_length=255, db_index=True)
    meta = models.TextField(blank=True)  # JSON dictionary
    fields_version = models.CharField(max_length=80)

    @classmethod
    def users_with_additional_profile(cls, course_id):
        profiles = cls.objects.filter(course_id=course_id)
        result = {}
        for profile in profiles:
            result[profile.user_id] = json.loads(profile.meta)
        return result

    def converted_meta(self):
        try:
            meta_dict = json.loads(self.meta)
        except ValueError:
            meta_dict = {}
        return meta_dict


class StudentAttributesRegistrationModel(object):
    """
    Helper model-like object to save registration properties.
    """
    data = None
    user = None

    def __init__(self, data):
        self.data = data

    def save(self):
        if self.data:
            for values in self.data:
                values['user'] = self.user
                CredoStudentProperties(**values).save()


def check_and_save_enrollment_attributes(post_data, user, course_id):
    try:
        properties = EnrollmentPropertiesPerCourse.objects.get(course_id=course_id)
        try:
            enrollment_properties = json.loads(properties.data)
        except ValueError:
            return
        if enrollment_properties:
            CredoStudentProperties.objects.filter(course_id=course_id, user=user).delete()
            for k, v in enrollment_properties.iteritems():
                lti_key = v['lti'] if 'lti' in v else False
                default = v['default'] if 'default' in v and v['default'] else None
                if lti_key:
                    if lti_key in post_data:
                        CredoStudentProperties(user=user, course_id=course_id,
                                               name=k, value=post_data[lti_key]).save()
                    elif default:
                        CredoStudentProperties(user=user, course_id=course_id,
                                               name=k, value=default).save()
            set_custom_term(course_id, user)

    except EnrollmentPropertiesPerCourse.DoesNotExist:
        return


def get_custom_term():
    return datetime.datetime.now().strftime("%B %Y")


def save_custom_term_student_property(term, user, course_id):
    return CredoStudentProperties.objects.get_or_create(user=user, course_id=course_id, name='term',
                                                        defaults={'value': term})


class CredoStudentProperties(models.Model):
    """
    This table contains info about the custom student properties.
    """
    class Meta(object):
        db_table = "credo_student_properties"
        ordering = ('user', 'course_id', 'name')

    user = models.ForeignKey(User)
    course_id = CourseKeyField(max_length=255, db_index=True, null=True, blank=True)
    name = models.CharField(max_length=255, db_index=True)
    value = models.CharField(max_length=255)


def validate_json_props(value):
    try:
        json_data = json.loads(value)
        if json_data:
            for key in json_data:
                if not re.match(r'\w+$', key):
                    raise ValidationError(
                        '%(key)s should contain only alphanumeric characters and underscores',
                        params={'key': key},
                    )
    except ValueError:
        raise ValidationError('Invalid JSON')


class RegistrationPropertiesPerMicrosite(models.Model):
    org = models.CharField(max_length=255, verbose_name='Org', unique=True)
    domain = models.CharField(max_length=255, verbose_name='Microsite Domain Name', unique=True)
    data = models.TextField(
        verbose_name="Registration Properties",
        help_text="Config in JSON format",
        validators=[validate_json_props]
    )

    class Meta(object):
        db_table = "credo_registration_properties"
        verbose_name = "registration properties item"
        verbose_name_plural = "registration properties per microsite"


class EnrollmentPropertiesPerCourse(models.Model):
    course_id = CourseKeyField(db_index=True, max_length=255)
    data = models.TextField(
        verbose_name="Enrollment Properties",
        help_text="Config in JSON format",
        validators=[validate_json_props]
    )

    class Meta(object):
        db_table = "credo_enrollment_properties"
        verbose_name = "enrollment properties item"
        verbose_name_plural = "enrollment properties per course"


def user_must_fill_additional_profile_fields(course, user, block=None):
    graded = block.graded if block else False
    course_key = course.id
    if graded and course.credo_additional_profile_fields and user.is_authenticated and\
            user.email.endswith('@credomodules.com') and CourseEnrollment.is_enrolled(user, course_key):
        fields_version = additional_profile_fields_hash(course.credo_additional_profile_fields)
        profiles = CredoModulesUserProfile.objects.filter(user=user, course_id=course_key)
        if len(profiles) == 0 or profiles[0].fields_version != fields_version:
            return True
    return False


class TermPerOrg(models.Model):
    org = models.CharField(max_length=255, verbose_name='Org', null=False, blank=False, db_index=True)
    term = models.CharField(max_length=255, verbose_name='Term', null=False, blank=False)
    start_date = models.DateField(verbose_name='Start Date', null=False, blank=False)
    end_date = models.DateField(verbose_name='End Date', null=False, blank=False)

    def to_dict(self):
        return {
            'id': self.id,
            'org': self.org,
            'term': self.term,
            'start_date': self.start_date.strftime('%-m/%-d/%Y'),
            'end_date': self.end_date.strftime('%-m/%-d/%Y')
        }


def set_custom_term(course_id, user):
    save_custom_term_student_property(get_custom_term(), user, course_id)


@receiver(ENROLL_STATUS_CHANGE)
def add_custom_term_student_property_on_enrollment(sender, event=None, user=None, course_id=None, **kwargs):
    if event == EnrollStatusChange.enroll:
        set_custom_term(course_id, user)


def deadlock_db_retry(func):
    def func_wrapper(*args, **kwargs):
        max_attempts = 2
        current_attempt = 0
        while True:
            try:
                return func(*args, **kwargs)
            except OperationalError, e:
                if current_attempt < max_attempts:
                    current_attempt += 1
                    time.sleep(3)
                else:
                    log.error('Failed to save course usage: ' + str(e))
                    return

    return func_wrapper


class CourseUsage(models.Model):
    MODULE_TYPES = (('problem', 'problem'),
                    ('video', 'video'),
                    ('html', 'html'),
                    ('course', 'course'),
                    ('chapter', 'Section'),
                    ('sequential', 'Subsection'),
                    ('vertical', 'Vertical'),
                    ('library_content', 'Library Content'))

    user = models.ForeignKey(User)
    course_id = CourseKeyField(max_length=255, db_index=True, null=True, blank=True)
    block_id = models.CharField(max_length=255, db_index=True, null=True)
    block_type = models.CharField(max_length=32, choices=MODULE_TYPES, null=True)
    usage_count = models.IntegerField(null=True)
    first_usage_time = models.DateTimeField(verbose_name='First Usage Time', null=True, blank=True)
    last_usage_time = models.DateTimeField(verbose_name='Last Usage Time', null=True, blank=True)
    session_ids = models.TextField(null=True, blank=True)

    class Meta:
        unique_together = (('user', 'course_id', 'block_id'),)

    @classmethod
    @deadlock_db_retry
    def _update_block_usage(cls, course_key, user_id, block_type, block_id, unique_user_id):
        course_usage = CourseUsage.objects.get(
            course_id=course_key,
            user_id=user_id,
            block_type=block_type,
            block_id=block_id
        )
        if unique_user_id not in course_usage.session_ids:
            with transaction.atomic():
                CourseUsage.objects.filter(course_id=course_key, user_id=user_id,
                                           block_id=block_id, block_type=block_type) \
                    .update(last_usage_time=usage_dt_now(), usage_count=F('usage_count') + 1,
                            session_ids=Concat('session_ids', Value('|'), Value(unique_user_id)))

    @classmethod
    @deadlock_db_retry
    def _add_block_usage(cls, course_key, user_id, block_type, block_id, unique_user_id):
        datetime_now = usage_dt_now()
        with transaction.atomic():
            cu = CourseUsage(
                course_id=course_key,
                user_id=user_id,
                usage_count=1,
                block_type=block_type,
                block_id=block_id,
                first_usage_time=datetime_now,
                last_usage_time=datetime_now,
                session_ids=unique_user_id
            )
            cu.save()
            return

    @classmethod
    def update_block_usage(cls, request, course_key, block_id):
        unique_user_id = get_unique_user_id(request)
        if unique_user_id and hasattr(request, 'user') and request.user.is_authenticated():
            if not isinstance(course_key, CourseKey):
                course_key = CourseKey.from_string(course_key)
            if not isinstance(block_id, UsageKey):
                block_id = UsageKey.from_string(block_id)
            block_type = block_id.block_type
            block_id = str(block_id)

            try:
                cls._update_block_usage(course_key, request.user.id,
                                        block_type, block_id, unique_user_id)
            except CourseUsage.DoesNotExist:
                try:
                    cls._add_block_usage(course_key, request.user.id, block_type, block_id, unique_user_id)
                    return
                except IntegrityError:
                    #cls._update_block_usage(course_key, request.user.id,
                    #                        block_type, block_id, unique_user_id)
                    return


class OrganizationType(models.Model):
    title = models.CharField(max_length=255, verbose_name='Title', unique=True)
    constructor_lti_link = models.BooleanField(default=True, verbose_name='Display LTI link in Constructor')
    constructor_embed_code = models.BooleanField(default=True, verbose_name='Display embed code field in Constructor')
    constructor_direct_link = models.BooleanField(default=True, verbose_name='Display direct link in Constructor')
    insights_learning_outcomes = models.BooleanField(default=True, verbose_name='Display LO report in Credo Insights')
    insights_assessments = models.BooleanField(default=True, verbose_name='Display Assessment report in Credo Insights')
    insights_enrollment = models.BooleanField(default=True, verbose_name='Display Enrollment report in Credo Insights')
    insights_engagement = models.BooleanField(default=True, verbose_name='Display Engagement report in Credo Insights')
    instructor_dashboard_credo_insights = models.BooleanField(default=True, verbose_name='Show Credo Insights link'
                                                                                         ' in the Instructor Dashboard')
    enable_new_carousel_view = models.BooleanField(default=False, verbose_name='Enable new carousel view'
                                                                               ' (horizontal nav bar)')
    enable_page_level_engagement = models.BooleanField(default=False, verbose_name='Enable Page Level for Engagement '
                                                                                   'Statistic in Insights')
    enable_extended_progress_page = models.BooleanField(default=False, verbose_name='Enable Extended Progress Page')

    class Meta:
        ordering = ['title']

    def __unicode__(self):
        return self.title

    @classmethod
    def get_all_constructor_fields(cls):
        return ['lti_link', 'embed_code', 'direct_link']

    def get_constructor_fields(self):
        data = []
        if self.constructor_lti_link:
            data.append('lti_link')
        if self.constructor_embed_code:
            data.append('embed_code')
        if self.constructor_direct_link:
            data.append('direct_link')
        return data

    @classmethod
    def get_all_insights_reports(cls):
        return ['learning_outcomes', 'assessments', 'enrollment', 'engagement']

    def get_insights_reports(self):
        data = []
        if self.insights_learning_outcomes:
            data.append('learning_outcomes')
        if self.insights_assessments:
            data.append('assessments')
        if self.insights_enrollment:
            data.append('enrollment')
        if self.insights_engagement:
            data.append('engagement')
        return data


class Organization(models.Model):
    org = models.CharField(max_length=255, verbose_name='Org', unique=True)
    default_frame_domain = models.CharField(max_length=255, verbose_name='Domain for LTI/Iframe/etc',
                                            help_text="Default value is https://frame.credocourseware.com "
                                                      "in case of empty field",
                                            null=True, blank=True,
                                            validators=[URLValidator()])
    org_type = models.ForeignKey(OrganizationType, on_delete=models.SET_NULL,
                                 related_name='org_type',
                                 null=True, blank=True, verbose_name='Org Type')

    def save(self, *args, **kwargs):
        if self.default_frame_domain:
            o = urlparse(self.default_frame_domain)
            self.default_frame_domain = o.scheme + '://' + o.netloc
        super(Organization, self).save(*args, **kwargs)

    def get_constructor_fields(self):
        if self.org_type:
            return self.org_type.get_constructor_fields()
        else:
            return OrganizationType.get_all_constructor_fields()

    def get_insights_reports(self):
        if self.org_type:
            return self.org_type.get_insights_reports()
        else:
            return OrganizationType.get_all_insights_reports()

    def get_page_level_engagement(self):
        if self.org_type:
            return self.org_type.enable_page_level_engagement
        else:
            return False

    def to_dict(self):
        return {
            'org': self.org,
            'default_frame_domain': self.default_frame_domain,
            'constructor_fields': self.get_constructor_fields(),
            'insights_reports': self.get_insights_reports(),
            'page_level_engagement': self.get_page_level_engagement(),
        }

    @property
    def is_carousel_view(self):
        if self.org_type is not None:
            return self.org_type.enable_new_carousel_view
        else:
            return False


class CourseExcludeInsights(models.Model):
    course_id = CourseKeyField(max_length=255, db_index=True, null=True, blank=True)

    class Meta(object):
        db_table = "credo_course_exclude_insights"
        verbose_name = "course"
        verbose_name_plural = "exclude insights"


class SendScores(models.Model):
    user = models.ForeignKey(User)
    course_id = CourseKeyField(max_length=255, db_index=True)
    block_id = models.CharField(max_length=255, db_index=True)
    last_send_time = models.DateTimeField(null=True, blank=True)

    class Meta(object):
        db_table = "credo_send_scores"
        unique_together = (('user', 'course_id', 'block_id'),)


class SendScoresMailing(models.Model):
    email_scores = models.ForeignKey(SendScores)
    data = models.TextField(blank=True)
    last_send_time = models.DateTimeField(null=True, blank=True)

    class Meta(object):
        db_table = "credo_send_scores_mailing"


UNIQUE_USER_ID_COOKIE = 'credo-course-usage-id'


def get_unique_user_id(request):
    uid = request.COOKIES.get(UNIQUE_USER_ID_COOKIE, None)
    if uid:
        return unicode(uid)
    return None


def generate_new_user_id_cookie(request, user_id):
    request._update_unique_user_id = True
    request.COOKIES[UNIQUE_USER_ID_COOKIE] = unicode(uuid.uuid4()) + '_' + user_id


def update_unique_user_id_cookie(request):
    user_id = 'anon'
    if hasattr(request, 'user') and request.user.is_authenticated():
        user_id = str(request.user.id)

    course_usage_cookie_id = get_unique_user_id(request)
    if not course_usage_cookie_id:
        generate_new_user_id_cookie(request, user_id)
    else:
        cookie_arr = course_usage_cookie_id.split('_')
        if len(cookie_arr) < 2 or cookie_arr[1] != user_id:
            generate_new_user_id_cookie(request, user_id)


def usage_dt_now():
    """
    We can't use timezone.now() because we already use America/New_York timezone for usage values
    so we just replace tzinfo in the datetime object
    :return: datetime
    """
    return datetime.datetime.now().replace(tzinfo=utc)
