from django.urls import include, path, re_path

from visor import views

urlpatterns = [
    path('', views.search, name='search'),
    path('search/', views.search, name='search'),
    path(r'admin/', include('massadmin.urls')),
    re_path(r'^graph/$', views.graph, name='graph'),
    re_path(r'^results/$', views.results, name='results'),
    re_path(r'^results/jump$', views.results, name='results_jump'),
    re_path(r'^export/$', views.export, name='export'),
    re_path(r'^bulk_export/$', views.bulk_export, name='bulk_export'),
    re_path(r'^meta/$', views.meta, name='meta'),
    path('admin_upload_image/', views.admin_upload_image,
         name="admin_upload_image"),
    path('admin_upload_image/<str:ids>', views.admin_upload_image,
         name="admin_upload_image"),
    path('upload', views.upload, name="upload"),
    re_path(r'^about/$', views.about, name='about'),
    re_path(r'^status/$', views.status, name='status'),
]
