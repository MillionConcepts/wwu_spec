#https://www.dev2qa.com/how-to-pass-parameters-to-view-via-url-in-django/
#https://stackoverflow.com/questions/32567808/how-do-i-pass-parameters-via-url-in-django
# https://docs.djangoproject.com/en/3.0/topics/http/urls/#passing-extra-options-to-view-functions
from django.contrib import admin
from django.http import HttpResponseRedirect
from django.shortcuts import render

from mars.models import Database,SampleType,Sample,FilterSet
from mars.forms import AdminUploadImageForm
from mars.views import admin_upload_image

def upload_sample_image(modelAdmin,request,queryset):
	samples=[sample.id for sample in queryset]
	return HttpResponseRedirect('/mars/admin_upload_image/'+str(samples))

upload_sample_image.short_description = "Upload Image"

class SampleAdmin(admin.ModelAdmin):
    actions = [upload_sample_image]

admin.site.register(Database)
admin.site.register(SampleType)
admin.site.register(Sample, SampleAdmin)
admin.site.register(FilterSet)