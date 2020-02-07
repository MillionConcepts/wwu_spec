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
from django.contrib import admin
from django.urls import path,re_path,include
from django.views.generic import RedirectView
from mars import views, forms, urls

# redirect base URL to Mars, given that currently we only serve Mars data

urlpatterns = [
    path('admin/', admin.site.urls),
    path('mars/', include('mars.urls')),
    path('', RedirectView.as_view(url='mars/',permanent=True)),
]

# use static() to serve static files during development
# remove for deployment

from django.conf import settings
from django.conf.urls.static import static

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

