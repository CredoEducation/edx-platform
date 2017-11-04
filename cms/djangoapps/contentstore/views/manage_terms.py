import datetime
import json

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.translation import ugettext as _

from credo_modules.models import TermPerOrg
from edxmako.shortcuts import render_to_response
from util.json_request import JsonResponse
from .course import get_courses_accessible_to_user, _remove_in_process_courses


__all__ = ['manage_terms', 'get_org_terms', 'save_org_term', 'remove_org_term']


def _get_user_orgs(request):
    courses, in_process_course_actions = get_courses_accessible_to_user(request)
    courses = _remove_in_process_courses(courses, in_process_course_actions)
    available_orgs = []
    for course in courses:
        available_orgs.append(course['org'])
    return sorted(list(set(available_orgs)))


@login_required
@ensure_csrf_cookie
def manage_terms(request):
    available_orgs = _get_user_orgs(request)

    return render_to_response('manage_terms.html', {
        'available_orgs': available_orgs,
        'get_org_terms_url': reverse('get_org_terms'),
        'save_org_term': reverse('save_org_term'),
        'remove_org_term': reverse('remove_org_term')
    })


@login_required
@ensure_csrf_cookie
def get_org_terms(request, org):
    available_orgs = _get_user_orgs(request)
    if org not in available_orgs:
        return JsonResponse({"success": False, "errorMessage": _("Invalid org")})

    data = TermPerOrg.objects.filter(org=org).order_by('term')
    return JsonResponse({"success": True, "data": [item.to_dict() for item in data]})


@login_required
@ensure_csrf_cookie
def save_org_term(request, org):
    available_orgs = _get_user_orgs(request)
    if org not in available_orgs:
        return JsonResponse({"success": False, "errorMessage": _("Invalid org")})

    try:
        posted_data = json.loads(request.body.decode('utf-8'))
    except ValueError:
        return JsonResponse({"success": False, "errorMessage": _("Invalid request")})

    post_required_params = {
        'title': 'Term',
        'startDate': 'Start Date',
        'endDate': 'End Date'
    }

    for k, v in post_required_params.iteritems():
        if k not in posted_data or posted_data[k].strip() == '':
            return JsonResponse({"success": False, "errorMessage": _(v + " field can't be empty")})

    term = posted_data['title'].strip()
    start_date = posted_data['startDate'].strip()
    end_date = posted_data['endDate'].strip()
    term_id = int(posted_data['id']) if 'id' in posted_data else None

    start_date_arr = start_date.split('/')
    start_date = datetime.date(int(start_date_arr[2]), int(start_date_arr[0]), int(start_date_arr[1]))

    end_date_arr = end_date.split('/')
    end_date = datetime.date(int(end_date_arr[2]), int(end_date_arr[0]), int(end_date_arr[1]))

    overlap_items = TermPerOrg.objects.filter(
        Q(org=org, start_date__lte=start_date, end_date__gte=start_date) |
        Q(org=org, start_date__lte=end_date, end_date__gte=end_date))

    if len(overlap_items) > 0:
        for overlap_item in overlap_items:
            if (term_id and term_id != overlap_item.id) or term_id is None:
                overlap_item_dict = overlap_item.to_dict()
                return JsonResponse({
                    "success": False,
                    "errorMessage": _("New term interval overlaps with the interval for"
                                      " \"%(term)s\" (%(start_date)s - %(end_date)s)" % overlap_item_dict)
                })

    if term_id:
        try:
            obj = TermPerOrg.objects.get(pk=term_id, org=org)
            obj.term = term
            obj.start_date = start_date
            obj.end_date = end_date
        except ObjectDoesNotExist:
            return JsonResponse({"success": False, "errorMessage": _("Term was not found")})
    else:
        obj = TermPerOrg(org=org, term=term, start_date=start_date, end_date=end_date)
    obj.save()
    return JsonResponse({"success": True, "term": {"id": obj.id}})


@login_required
@ensure_csrf_cookie
def remove_org_term(request, org):
    available_orgs = _get_user_orgs(request)
    if org not in available_orgs:
        return JsonResponse({"success": False, "errorMessage": _("Invalid org")})

    try:
        posted_data = json.loads(request.body.decode('utf-8'))
    except ValueError:
        return JsonResponse({"success": False, "errorMessage": _("Invalid request")})

    term_id = int(posted_data['id']) if 'id' in posted_data else None
    if term_id:
        TermPerOrg.objects.filter(id=term_id, org=org).delete()

    return JsonResponse({"success": True})
