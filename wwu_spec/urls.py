"""wwu_spec URL Configuration"""
# import debug_toolbar
from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

# redirect base URL to VISOR

urlpatterns = [
    path('admin/', admin.site.urls),
    path('visor/', include('visor.urls')),
    path('', RedirectView.as_view(url='visor/', permanent=True)),
]

# if settings.DEBUG:
#     import debug_toolbar
#
#     urlpatterns.append(
#         path('__debug__/', include(debug_toolbar.urls))
#     )

from django.conf import settings
from django.conf.urls.static import static

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
