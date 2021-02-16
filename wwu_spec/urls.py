"""wwu_spec URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# import debug_toolbar
from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

# redirect base URL to Mars, given that currently we only serve Mars data

urlpatterns = [
    path('admin/', admin.site.urls),
    path('mars/', include('mars.urls')),
    path('', RedirectView.as_view(url='mars/', permanent=True)),
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
