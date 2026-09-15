from django import template
from django.template.defaultfilters import stringfilter

import re

register = template.Library()

# use with {% load chiron_tags %}


@register.filter
@stringfilter
def title2(s):
    return re.sub(r"(^|\s)(\S)", lambda m: m.group(1) + m.group(2).upper(), s)


@register.filter
def show_as_bool(value, appended_text=""):
    if value:
        template = '<strong class="text-danger"><i class="fas fa-check-circle"></i> {}</strong>'
        return template.format(appended_text)
    return '<strong class="text-success"><i class="fas fa-times-circle"></i> {}</strong>'.format(
        appended_text
    )


@register.filter
def keyvalue(dict, key):
    """
    Get a dict value by key when your key is stored in a variable

    USAGE: {{ mydict|keyvalue:mykey }}
    """
    if key in dict:
        return dict[key]
    return ""


@register.filter
def zero_is_bad(value, appended_text=""):
    if value in [0, "0"]:
        return '<strong class="text-danger">{} {}</strong>'.format(value, appended_text)
    return '<strong class="text-success">{} {}</strong>'.format(value, appended_text)


@register.filter
def times(count):
    return range(int(count))
