"""
LTI Provider view functions
"""
import json
import logging
import hashlib
import time

from collections import OrderedDict
from django.conf import settings
from django.http import Http404, HttpResponseBadRequest, HttpResponseForbidden, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey, UsageKey
from django.core.cache import caches

from lti_provider.models import LtiConsumer
from lti_provider.outcomes import store_outcome_parameters
from lti_provider.signature_validator import SignatureValidator
from lti_provider.users import authenticate_lti_user, update_lti_user_data
from openedx.core.lib.url_utils import unquote_slashes
from student.models import CourseEnrollment
from student.roles import CourseStaffRole
from util.views import add_p3p_header
from credo_modules.models import check_and_save_enrollment_attributes
from edxmako.shortcuts import render_to_string
from mako.template import Template
from courseware.courses import update_lms_course_usage


log = logging.getLogger("edx.lti_provider")

LTI_PARAM_EMAIL = 'lis_person_contact_email_primary'
LTI_PARAM_FIRST_NAME = 'lis_person_name_given'
LTI_PARAM_LAST_NAME = 'lis_person_name_family'

# LTI launch parameters that must be present for a successful launch
REQUIRED_PARAMETERS = [
    'roles', 'context_id', 'oauth_version', 'oauth_consumer_key',
    'oauth_signature', 'oauth_signature_method', 'oauth_timestamp',
    'oauth_nonce', 'user_id'
]

REQUIRED_PARAMETERS_STRICT = [
    'resource_link_id', 'lti_version', 'lti_message_type'
]

OPTIONAL_PARAMETERS = [
    'lis_result_sourcedid', 'lis_outcome_service_url',
    LTI_PARAM_EMAIL, LTI_PARAM_FIRST_NAME, LTI_PARAM_LAST_NAME,
    'tool_consumer_instance_guid'
]

@csrf_exempt
@add_p3p_header
def lti_launch(request, course_id, usage_id):
    """
    Endpoint for all requests to embed edX content via the LTI protocol. This
    endpoint will be called by a POST message that contains the parameters for
    an LTI launch (we support version 1.2 of the LTI specification):
        http://www.imsglobal.org/lti/ltiv1p2/ltiIMGv1p2.html

    An LTI launch is successful if:
        - The launch contains all the required parameters
        - The launch data is correctly signed using a known client key/secret
          pair
    """
    if not settings.FEATURES['ENABLE_LTI_PROVIDER']:
        return HttpResponseForbidden()

    # Check the LTI parameters, and return 400 if any required parameters are
    # missing
    start = time.time()
    request_params, is_cached = get_params(request)
    params = get_required_parameters(request_params)
    return_url = request_params.get('launch_presentation_return_url', None)

    end = time.time() - start
    log.info("Check the LTI parameters. during %s,  %s or usage key %s from request %s" % (end, course_id, usage_id, request))

    if not params:
        return render_bad_request(return_url)
    params.update(get_optional_parameters(request_params))

    # Get the consumer information from either the instance GUID or the consumer
    # key
    start = time.time()
    try:
        lti_consumer = LtiConsumer.get_or_supplement(
            params.get('tool_consumer_instance_guid', None),
            params['oauth_consumer_key']
        )
    except LtiConsumer.DoesNotExist:
        return render_response_forbidden(return_url)

    if lti_consumer.lti_strict_mode:
        params_strict = get_required_strict_parameters(request_params)
        if not params_strict or params_strict['lti_version'] != 'LTI-1p0' \
                or params_strict['lti_message_type'] != 'basic-lti-launch-request':
            return render_bad_request(return_url)
        params.update(params_strict)

        end = time.time() - start
    log.info("Get the consumer information. during %s,  %s or usage key %s from request %s" % (end,
          course_id,
          usage_id,
          request))

    # Check the OAuth signature on the message
    if not is_cached and not SignatureValidator(lti_consumer).verify(request):
        return render_response_forbidden(return_url)

    start = time.time()
    # Add the course and usage keys to the parameters array
    try:
        course_key, usage_key = parse_course_and_usage_keys(course_id, usage_id)
    except InvalidKeyError:
        log.error(
            'Invalid course key %s or usage key %s from request %s',
            course_id,
            usage_id,
            request
        )
        raise Http404()
    params['course_key'] = course_key
    params['usage_key'] = usage_key

    end = time.time() - start
    log.info("Add the course and usage keys. during %s,  %s or usage key %s from request %s" % (end,
          course_id,
          usage_id,
          request))

    if not is_cached:
        start = time.time()
        cache = caches['default']
        json_params = json.dumps(request.POST)
        params_hash = hashlib.md5(json_params).hexdigest()
        cache_key = ':'.join([settings.EMBEDDED_CODE_CACHE_PREFIX, params_hash])
        cache.set(cache_key, json_params, settings.EMBEDDED_CODE_CACHE_TIMEOUT)
        template = Template(render_to_string('static_templates/embedded_new_tab.html', {
            'disable_accordion': True,
            'allow_iframing': True,
            'disable_header': True,
            'disable_footer': True,
            'disable_window_wrap': True,
            'hash': params_hash,
            'additional_url_params': ''
        }))
        end = time.time() - start
        log.info("Render Embedded new tab. during %s,  %s or usage key %s from request %s" % (end,
              course_id,
              usage_id,
              request))
        return HttpResponse(template.render())

    # Create an edX account if the user identifed by the LTI launch doesn't have
    # one already, and log the edX account into the platform.
    start = time.time()
    lti_params = {}
    lti_keys = {LTI_PARAM_EMAIL: 'email', LTI_PARAM_FIRST_NAME: 'first_name', LTI_PARAM_LAST_NAME: 'last_name'}
    for key in lti_keys:
        if key in params:
            lti_params[lti_keys[key]] = params[key]
    authenticate_lti_user(request, params['user_id'], lti_consumer, lti_params)
    if request.user.is_authenticated():
        roles = params.get('roles', None) if lti_consumer.allow_to_add_instructors_via_lti else None
        enroll_result = enroll_user_to_course(request.user, course_key, roles)
        if enroll_result:
            check_and_save_enrollment_attributes(request_params, request.user, course_key)
        if lti_params and 'email' in lti_params:
            update_lti_user_data(request.user, lti_params['email'])

    end = time.time() - start
    log.info("Create an edX account. during %s,  %s or usage key %s from request %s" % (end,
          course_id,
          usage_id,
          request))

    # Store any parameters required by the outcome service in order to report
    # scores back later. We know that the consumer exists, since the record was
    # used earlier to verify the oauth signature.
    start = time.time()
    store_outcome_parameters(params, request.user, lti_consumer)
    update_lms_course_usage(request, usage_key, course_key)

    end = time.time() - start
    log.info("update_lms_course_usage. during %s,  %s or usage key %s from request %s" % (end,
          course_id,
          usage_id,
          request))

    start = time.time()
    result = render_courseware(request, params['usage_key'])
    end = time.time() - start
    log.info("render_courseware. during %s,  %s or usage key %s from request %s" % (end,
          course_id,
          usage_id,
          request))

    return result


def test_launch(request):
    headers = OrderedDict()
    if 'CONTENT_LENGTH' in request.META:
        headers['Content-Length'] = str(request.META['CONTENT_LENGTH'])
    if 'CONTENT_TYPE' in request.META:
        headers['Content-Type'] = str(request.META['CONTENT_TYPE'])
    for header, value in request.META.items():
        if not header.startswith('HTTP'):
            continue
        header = '-'.join([h.capitalize() for h in header[5:].lower().split('_')])
        headers[header] = str(value)

    params = get_required_parameters(request.POST)
    if params:
        params.update(get_optional_parameters(request.POST))
    else:
        params = {}

    lti_consumer = None
    try:
        lti_consumer = LtiConsumer.get_or_supplement(
            params.get('tool_consumer_instance_guid', None),
            params.get('oauth_consumer_key', None)
        )
        lti_consumer_info = [
            'id: ' + str(lti_consumer.id),
            'consumer_name: ' + str(lti_consumer.consumer_name),
            'consumer_key: ' + str(lti_consumer.consumer_key),
            'lti_strict_mode: ' + str(lti_consumer.lti_strict_mode),
            'allow_to_add_instructors_via_lti: ' + str(lti_consumer.allow_to_add_instructors_via_lti)
        ]
    except LtiConsumer.DoesNotExist:
        lti_consumer_info = ['Not Found']
    except:
        lti_consumer_info = ['Invalid params']

    if lti_consumer and lti_consumer.lti_strict_mode:
        params_strict = get_required_strict_parameters(request.POST)
        if not params_strict or params_strict['lti_version'] != 'LTI-1p0' \
                or params_strict['lti_message_type'] != 'basic-lti-launch-request':
            lti_consumer_info.append('LTI strict params validation failed!')
        params.update(params_strict)

    # Check the OAuth signature on the message
    signature_validation = '-'
    try:
        if lti_consumer:
            if SignatureValidator(lti_consumer).verify(request):
                signature_validation = 'Success'
            else:
                signature_validation = 'Failed'
    except:
        signature_validation = 'Error'

    post = OrderedDict()
    for post_key, post_value in request.POST.items():
        post[str(post_key)] = str(post_value)

    template = Template(render_to_string('static_templates/debug.html', {
        'disable_accordion': True,
        'allow_iframing': True,
        'disable_header': True,
        'disable_footer': True,
        'disable_window_wrap': True,
        'request_path': request.path,
        'request_method': request.method,
        'lti_consumer_info': lti_consumer_info,
        'signature_validation': signature_validation,
        'headers_data': headers,
        'post_data': post
    }))
    return HttpResponse(template.render())


def enroll_user_to_course(edx_user, course_key, roles=None):
    """
    Enrolles the user to the course if he is not already enrolled.
    """
    if course_key is not None and not CourseEnrollment.is_enrolled(edx_user, course_key):
        CourseEnrollment.enroll(edx_user, course_key)
        if roles:
            set_user_roles(edx_user, course_key, roles)
        return True
    return False


def get_required_parameters(dictionary, additional_params=None):
    """
    Extract all required LTI parameters from a dictionary and verify that none
    are missing.

    :param dictionary: The dictionary that should contain all required parameters
    :param additional_params: Any expected parameters, beyond those required for
        the LTI launch.

    :return: A new dictionary containing all the required parameters from the
        original dictionary and additional parameters, or None if any expected
        parameters are missing.
    """
    params = {}
    additional_params = additional_params or []
    for key in REQUIRED_PARAMETERS + additional_params:
        if key not in dictionary:
            return None
        params[key] = dictionary[key]
    return params


def get_optional_parameters(dictionary):
    """
    Extract all optional LTI parameters from a dictionary. This method does not
    fail if any parameters are missing.

    :param dictionary: A dictionary containing zero or more optional parameters.
    :return: A new dictionary containing all optional parameters from the
        original dictionary, or an empty dictionary if no optional parameters
        were present.
    """
    return {key: dictionary[key] for key in OPTIONAL_PARAMETERS if key in dictionary}


def render_courseware(request, usage_key):
    """
    Render the content requested for the LTI launch.
    TODO: This method depends on the current refactoring work on the
    courseware/courseware.html template. It's signature may change depending on
    the requirements for that template once the refactoring is complete.

    Return an HttpResponse object that contains the template and necessary
    context to render the courseware.
    """
    # return an HttpResponse object that contains the template and necessary context to render the courseware.
    from courseware.views.views import render_xblock
    return render_xblock(request, unicode(usage_key), check_if_enrolled=False)


def parse_course_and_usage_keys(course_id, usage_id):
    """
    Convert course and usage ID strings into key objects. Return a tuple of
    (course_key, usage_key), or throw an InvalidKeyError if the translation
    fails.
    """
    course_key = CourseKey.from_string(course_id)
    usage_id = unquote_slashes(usage_id)
    usage_key = UsageKey.from_string(usage_id).map_into_course(course_key)
    return course_key, usage_key


def get_required_strict_parameters(dictionary):
    """
    Extract all required LTI parameters (consumer strict mode) from a dictionary and verify that none
    are missing.
    """
    params = {}
    for key in REQUIRED_PARAMETERS_STRICT:
        if key not in dictionary:
            return None
        params[key] = dictionary[key]
    return params


def render_bad_request(return_url):
    """
    Render the error template and log an Http 400 error on invalid launch
    (required by IMS)
    """
    template400 = Template(render_to_string('static_templates/400.html', {'return_url': return_url}))
    return HttpResponseBadRequest(template400.render())


def render_response_forbidden(return_url):
    """
    Render the error template and log an Http 403 error on invalid launch
    (required by IMS)
    """
    template403 = Template(render_to_string('static_templates/403.html', {'return_url': return_url}))
    return HttpResponseForbidden(template403.render())


def get_params(request):

    """
    Getting params from request or from cache
    :param request: request
    :return: dictionary of params, flag: from cache or not
    """
    if request.GET.get('hash'):
        cache = caches['default']
        cached = cache.get(':'.join([settings.EMBEDDED_CODE_CACHE_PREFIX, request.GET.get('hash')]))
        if cached:
            return json.loads(cached), True
    return request.POST, False


def set_user_roles(edx_user, course_key, roles):
    # LIS vocabulary for System Role
    # https://www.imsglobal.org/specs/ltiv1p0/implementation-guide#toc-9
    external_roles = ['Administrator', 'Instructor', 'Staff']
    if any(role in roles for role in external_roles):
        CourseStaffRole(course_key).add_users(edx_user)
