from django.conf import settings
from django.http import HttpRequest
from django.shortcuts import redirect
from django.urls import reverse


def human_required(view_function):
    def wrapper(request: HttpRequest, *args, **kwargs):
        if request.session.get('human', False) or not settings.DJANGOBOARD_REQUIRE_CAPTCHA:
            return view_function(request, *args, **kwargs)
        else:
            return redirect(reverse('djangoboard:captcha'))

    return wrapper
