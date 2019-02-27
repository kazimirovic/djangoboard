import os

from django import template

register = template.Library()


@register.filter
def filename(value):
    return os.path.basename(value.file.name)


@register.filter
def short_filename(value):
    l = 10
    name, ext = os.path.basename(value.file.name).rsplit('.', 1)
    return "%s.%s" % (name if len(name) < l else "%s.." % (name[:l]), ext)
