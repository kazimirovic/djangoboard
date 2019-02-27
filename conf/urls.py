from django.conf.urls import url
from django.contrib import admin
from django.http import HttpResponseNotFound
from django.urls import path, include

urlpatterns = [
    path('', include('djangoboard.urls')),
    path('admin/', admin.site.urls),

    # default password reset view could potentially give out our IP address, we don't want that
    path('accounts/password_reset/', lambda request: HttpResponseNotFound()),

    path('accounts/', include('django.contrib.auth.urls')),

    url(r'^captcha/', include('captcha.urls')),
]
