from django.contrib import admin
from .models import RegistrationPropertiesPerMicrosite, EnrollmentPropertiesPerCourse,\
    Organization, OrganizationType, CourseExcludeInsights, CourseUsage


class RegistrationPropertiesPerMicrositeForm(admin.ModelAdmin):
    list_display = ('id', 'org', 'domain')


class EnrollmentPropertiesPerCourseForm(admin.ModelAdmin):
    list_display = ('id', 'course_id')


class OrganizationForm(admin.ModelAdmin):
    list_display = ('id', 'org', 'org_type', 'default_frame_domain')


class OrganizationTypeForm(admin.ModelAdmin):
    list_display = ('id', 'title')


class CourseExcludeInsightsForm(admin.ModelAdmin):
    list_display = ('id', 'course_id')

    def get_actions(self, request):
        actions = super(CourseExcludeInsightsForm, self).get_actions(request)
        actions['delete_selected'][0].short_description = "Delete Selected"
        return actions


class CourseUsageForm(admin.ModelAdmin):
    list_display = ('course_id', 'usage_count', 'user_id', 'block_id', 'block_type',
                    'first_usage_time', 'last_usage_time')
    search_fields = ('course_id', 'user__id', 'user__username', 'block_id',)
    list_display_links = None

    def __init__(self, *args, **kwargs):
        super(CourseUsageForm, self).__init__(*args, **kwargs)

    def has_add_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        return []


admin.site.register(RegistrationPropertiesPerMicrosite, RegistrationPropertiesPerMicrositeForm)
admin.site.register(EnrollmentPropertiesPerCourse, EnrollmentPropertiesPerCourseForm)
admin.site.register(Organization, OrganizationForm)
admin.site.register(OrganizationType, OrganizationTypeForm)
admin.site.register(CourseExcludeInsights, CourseExcludeInsightsForm)
admin.site.register(CourseUsage, CourseUsageForm)
