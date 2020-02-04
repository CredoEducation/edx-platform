from credo.auth_helper import get_request_referer_from_other_domain, get_saved_referer, save_referer
from credo_modules.models import CourseUsage, CourseUsageLogEntry, usage_dt_now, get_student_properties,\
    update_unique_user_id_cookie, get_unique_user_id, UNIQUE_USER_ID_COOKIE
from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import F
from openedx.core.djangoapps.site_configuration.helpers import get_value
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey, UsageKey
from xmodule.modulestore.django import modulestore

try:
    import Cookie
except ImportError:
    import http.cookies as Cookie
try:
    from django.utils.deprecation import MiddlewareMixin
except ImportError:
    MiddlewareMixin = object


Cookie.Morsel._reserved['samesite'] = 'SameSite'


class RefererSaveMiddleware(object):
    def process_response(self, request, response):

        referer_url = get_request_referer_from_other_domain(request)
        if referer_url:
            saved_referer = get_saved_referer(request)
            if not saved_referer or saved_referer != referer_url:
                save_referer(response, referer_url)

        return response


class CourseUsageMiddleware(object):

    def _process_goto_position_urls(self, request, course_id, path_data):
        # handle URLs like
        # http://<lms_url>/courses/<course-id>/xblock/<block-id>/handler/xmodule_handler/goto_position
        if path_data[-1] == 'goto_position':
            block_id = None
            try:
                block_id = path_data[4]
            except IndexError:
                pass
            if block_id:
                course_key = CourseKey.from_string(course_id)
                position = int(request.POST.get('position', None)) - 1
                item = modulestore().get_item(UsageKey.from_string(block_id))
                if position is not None and hasattr(item, 'position'):
                    try:
                        child = item.get_children()[position]
                        student_properties = get_student_properties(request, course_key, child)
                        CourseUsage.update_block_usage(request, course_key, child.location, student_properties)
                    except IndexError:
                        pass

    def process_request(self, request):
        request.csrf_processing_done = True  # ignore CSRF check for the django REST framework
        update_unique_user_id_cookie(request)

    def process_response(self, request, response):
        path = request.path
        path_data = path.split('/')

        if hasattr(request, 'user') and request.user.is_authenticated and len(path_data) > 2:
            course_id = None
            if path_data[1] == 'lti_provider':
                if len(path_data) > 3:
                    course_id = path_data[3]
            else:
                course_id = path_data[2]

            sess_cookie_domain = get_value('SESSION_COOKIE_DOMAIN', settings.SESSION_COOKIE_DOMAIN)
            cookie_domain = sess_cookie_domain if sess_cookie_domain else None

            unique_user_id = get_unique_user_id(request)
            if unique_user_id and getattr(request, '_update_unique_user_id', False):
                response.set_cookie(UNIQUE_USER_ID_COOKIE, unique_user_id, path='/', domain=cookie_domain,
                                    secure=getattr(settings, 'SESSION_COOKIE_SECURE', False))

            datetime_now = usage_dt_now()
            if course_id and not CourseUsage.is_viewed(request, course_id):
                try:
                    course_key = CourseKey.from_string(course_id)
                    CourseUsage.mark_viewed(request, course_id)
                    student_properties = get_student_properties(request, course_key)

                    try:
                        CourseUsage.objects.get(
                            course_id=course_key,
                            user_id=request.user.id,
                            block_type='course',
                            block_id='course'
                        )
                        CourseUsage.objects.filter(course_id=course_key, user_id=request.user.id,
                                                   block_type='course', block_id='course') \
                            .update(last_usage_time=datetime_now, usage_count=F('usage_count') + 1)
                    except CourseUsage.DoesNotExist:
                        try:
                            with transaction.atomic():
                                cu = CourseUsage(
                                    course_id=course_key,
                                    user_id=request.user.id,
                                    usage_count=1,
                                    block_type='course',
                                    block_id='course',
                                    first_usage_time=datetime_now,
                                    last_usage_time=datetime_now
                                )
                                cu.save()
                        except IntegrityError:
                            CourseUsage.objects.filter(course_id=course_key, user_id=request.user.id,
                                                       block_type='course', block_id='course') \
                                .update(last_usage_time=datetime_now, usage_count=F('usage_count') + 1)

                    CourseUsageLogEntry.add_new_log(request.user.id, str(course_key), 'course', 'course',
                                                    student_properties)
                except InvalidKeyError:
                    pass

            # Update usage of vertical blocks
            self._process_goto_position_urls(request, course_id, path_data)

        return response


class CookiesSameSite(MiddlewareMixin):
    """
    Support for SameSite attribute in Cookies is implemented in Django 2.1 and won't
    be backported to Django 1.11.x.
    This middleware will be obsolete when your app will start using Django 2.1.
    """
    def process_response(self, request, response):
        protected_cookies = getattr(
            settings,
            'SESSION_COOKIE_SAMESITE_KEYS',
            set()
        ) or set()

        if not isinstance(protected_cookies, (list, set, tuple)):
            raise ValueError('SESSION_COOKIE_SAMESITE_KEYS should be a list, set or tuple.')

        protected_cookies = set(protected_cookies)
        protected_cookies |= {settings.SESSION_COOKIE_NAME, settings.CSRF_COOKIE_NAME}

        samesite_flag = getattr(
            settings,
            'SESSION_COOKIE_SAMESITE',
            None
        )

        if not samesite_flag:
            return response

        if samesite_flag.lower() not in {'lax', 'none', 'strict'}:
            raise ValueError('samesite must be "lax", "none", or "strict".')

        samesite_force_all = getattr(
            settings,
            'SESSION_COOKIE_SAMESITE_FORCE_ALL',
            False
        )
        if samesite_force_all:
            for cookie in response.cookies:
                response.cookies[cookie]['samesite'] = samesite_flag.lower()
        else:
            for cookie in protected_cookies:
                if cookie in response.cookies:
                    response.cookies[cookie]['samesite'] = samesite_flag.lower()

        return response
