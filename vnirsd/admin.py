# https://www.dev2qa.com/how-to-pass-parameters-to-view-via-url-in-django/
# https://stackoverflow.com/questions/32567808/how-do-i-pass-parameters-via
# -url-in-django https://docs.djangoproject.com/en/3.0/topics/http/urls
# /#passing-extra-options-to-view-functions
from django.contrib import admin
from django.http import HttpResponseRedirect

from vnirsd.models import Database, SampleType, Sample, FilterSet, Library


def upload_sample_image(model_admin, request, queryset):
    samples = [sample.id for sample in queryset]
    return HttpResponseRedirect('/vnirsd/admin_upload_image/' + str(samples))


upload_sample_image.short_description = "Upload Image"


class SampleAdmin(admin.ModelAdmin):
    actions = [upload_sample_image]


admin.site.register(Database)
admin.site.register(Library)
admin.site.register(SampleType)
admin.site.register(Sample, SampleAdmin)
admin.site.register(FilterSet)
