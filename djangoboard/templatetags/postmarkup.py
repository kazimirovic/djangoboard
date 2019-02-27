import re

from django import template
from django.urls import reverse
from django.utils.html import escape, linebreaks, mark_safe

register = template.Library()


def find_all_replies(text):
    return re.findall(re.compile(r'(?<!>)>>(\d+)'), text)


@register.filter('get_post_link')
def get_post_link(number, displayed_post_ids):
    if int(number) not in displayed_post_ids:
        link = reverse('djangoboard:post', args=[number])
    else:
        link = '#%s' % number
    return mark_safe('<a href="%s">&gt;&gt;%s</a>' % (link, number))


def get_thread_link(number):
    link = reverse('djangoboard:thread', args=[number])
    return '<a href="%s">&gt;&gt;&gt;%s</a>' % (link, number)


def get_board_link(name):
    link = reverse('djangoboard:board', args=[name])
    return '<a href="%s">&gt;&gt;&gt;&gt;%s</a>' % (link, name)


@register.filter('postmarkup')
def postmarkup(text, displayed_post_ids=[]):
    if text:
        text = linebreaks(escape(text))
        replacements = (
            (re.compile(r'&gt;&gt;&gt;&gt;([^\s<]*)'),
             lambda match: get_board_link(match.group(1))),  # ">>>number" links (boards)

            (re.compile(r'&gt;&gt;&gt;(\d+)'),
             lambda match: get_thread_link(match.group(1))),  # ">>>number" links (threads)

            (re.compile(r'(?<!&gt;)(&gt;&gt;)(\d+)'),
             lambda match: get_post_link(match.group(2), displayed_post_ids)),  # ">>number" links (posts)

            (re.compile(r'(?<!&gt;)(&gt;[^&\d<].+?)(?=<)'), r'<span class="quote">\1</span>'),  # quotes
            (re.compile(r'(?<!&gt;)(&lt;[^&].+?)(?=<)'), r'<span class="orange">\1</span>'),  # orange quotes
        )
        for old, new in replacements:
            text = re.sub(old, new, text)
        return mark_safe(text)
    return ''
