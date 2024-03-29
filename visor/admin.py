from django.contrib import admin
from django.http import HttpResponseRedirect

from visor.models import Database, SampleType, Sample, FilterSet, Library


def upload_sample_image(model_admin, request, queryset):
    samples = [sample.id for sample in queryset]
    return HttpResponseRedirect("/visor/admin_upload_image/" + str(samples))


upload_sample_image.short_description = "Upload Image"


class SampleAdmin(admin.ModelAdmin):
    actions = [upload_sample_image]


admin.site.register(Database)
admin.site.register(Library)
admin.site.register(SampleType)
admin.site.register(Sample, SampleAdmin)
admin.site.register(FilterSet)
