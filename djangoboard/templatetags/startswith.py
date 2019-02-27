from django import template

register = template.Library()


@register.filter('startswith')
def startswith(text, starts):
    try:
        return str(text).startswith(starts)
    except AttributeError:
        return False
