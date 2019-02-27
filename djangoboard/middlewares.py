from django.core.exceptions import PermissionDenied

from .models import IP


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


class FilterI2pDestMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        dest, _ = IP.objects.get_or_create(ip=get_client_ip(request))
        if dest.banned:
            raise PermissionDenied
        else:
            request.i2p_destination = dest

        return self.get_response(request)
