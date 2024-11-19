from django.contrib import admin
from django.http import HttpResponseRedirect

from visor.models import Database, SampleType, Sample, FilterSet, Library



admin.site.register(Database)
admin.site.register(Library)
admin.site.register(SampleType)
admin.site.register(FilterSet)
