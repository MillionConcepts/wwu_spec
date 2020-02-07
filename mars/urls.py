from django.urls import include, path, re_path
from django.views.generic import RedirectView

from mars import views, forms

urlpatterns = [
	path('', views.search, name='search'),
    path('search/',views.search,name='search'),

    path(r'admin/', include('massadmin.urls')),
    re_path(r'^graph/$', views.graph, name='graph'),
    re_path(r'^results/$', views.results,name='results'),
    re_path(r'^export/$',views.export,name='export'),
    re_path(r'^meta/$',views.meta,name='meta'),
    re_path(r'^flagSample/$', views.flag_sample, name='flag_sample'),
    path('admin_upload_image/<str:ids>',views.admin_upload_image,name="admin_upload_image"),
    path('upload',views.upload,name="upload"),
    re_path(r'^about/$',views.about,name='about'),



    #debug


    path('search_strip/',views.search_strip,name='search_strip'),
    path('test/',views.test,name='test'),
   
    ]
    
