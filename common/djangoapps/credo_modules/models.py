import datetime
import json
import re
import uuid
from urlparse import urlparse
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.db import models, IntegrityError
from django.db.models import F, Value
from django.db.models.functions import Concat
from openedx.core.djangoapps.xmodule_django.models import CourseKeyField
from opaque_keys.edx.keys import CourseKey, UsageKey
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator

from credo_modules.utils import additional_profile_fields_hash
from student.models import CourseEnrollment, ENROLL_STATUS_CHANGE, EnrollStatusChange


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
    except EnrollmentPropertiesPerCourse.DoesNotExist:
        return


def get_custom_term(org):
    current_date = datetime.date.today()
    data = TermPerOrg.objects.filter(org=org, start_date__lte=current_date, end_date__gte=current_date)
    if len(data) > 0:
        return data[0]
    return None


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
    if graded and course.credo_additional_profile_fields and user.email.endswith('@credomodules.com') \
            and CourseEnrollment.is_enrolled(user, course_key):
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


@receiver(ENROLL_STATUS_CHANGE)
def add_custom_term_student_property_on_enrollment(sender, event=None, user=None, course_id=None, **kwargs):
    if event == EnrollStatusChange.enroll:
        item = get_custom_term(course_id.org)
        if item:
            save_custom_term_student_property(item.term, user, course_id)


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
    def _add_block_usage(cls, course_key, user_id, block_type, block_id, unique_user_id):
        course_usage = CourseUsage.objects.get(
            course_id=course_key,
            user_id=user_id,
            block_type=block_type,
            block_id=block_id
        )
        if unique_user_id not in course_usage.session_ids:
            CourseUsage.objects.filter(course_id=course_key, user_id=user_id,
                                       block_id=block_id, block_type=block_type) \
                .update(last_usage_time=datetime.datetime.now(), usage_count=F('usage_count') + 1,
                        session_ids=Concat('session_ids', Value('|'), Value(unique_user_id)))

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
                cls._add_block_usage(course_key, request.user.id,
                                     block_type, block_id, unique_user_id)
            except CourseUsage.DoesNotExist:
                datetime_now = datetime.datetime.now()
                try:
                    cu = CourseUsage(
                        course_id=course_key,
                        user_id=request.user.id,
                        usage_count=1,
                        block_type=block_type,
                        block_id=block_id,
                        first_usage_time=datetime_now,
                        last_usage_time=datetime_now,
                        session_ids=unique_user_id
                    )
                    cu.save()
                except IntegrityError:
                    cls._add_block_usage(course_key, request.user.id,
                                         block_type, block_id, unique_user_id)


class Organization(models.Model):
    org = models.CharField(max_length=255, verbose_name='Org', unique=True)
    default_frame_domain = models.CharField(max_length=255, verbose_name='Domain for LTI/Iframe/etc',
                                            help_text="Default value is https://frame.credocourseware.com "
                                                      "in case of empty field",
                                            null=True, blank=True,
                                            validators=[URLValidator()])
    is_courseware_customer = models.BooleanField(default=False, verbose_name='Courseware customer')
    is_skill_customer = models.BooleanField(default=False, verbose_name='SKILL customer')
    is_modules_customer = models.BooleanField(default=False, verbose_name='Modules customer')

    def to_dict(self):
        return {
            'org': self.org,
            'default_frame_domain': self.default_frame_domain,
            'is_courseware_customer': self.is_courseware_customer,
            'is_skill_customer': self.is_skill_customer,
            'is_modules_customer': self.is_modules_customer,
        }

    def save(self, *args, **kwargs):
        if self.default_frame_domain:
            o = urlparse(self.default_frame_domain)
            self.default_frame_domain = o.scheme + '://' + o.netloc
        super(Organization, self).save(*args, **kwargs)


class CourseExcludeInsights(models.Model):
    course_id = CourseKeyField(max_length=255, db_index=True, null=True, blank=True)

    class Meta(object):
        db_table = "credo_course_exclude_insights"
        verbose_name = "course"
        verbose_name_plural = "exclude insights"


UNIQUE_USER_ID_COOKIE = 'credo-course-usage-id'


def get_unique_user_id(request):
    return request.COOKIES.get(UNIQUE_USER_ID_COOKIE, None)


def set_unique_user_id(request):
    request.COOKIES[UNIQUE_USER_ID_COOKIE] = uuid.uuid4()
