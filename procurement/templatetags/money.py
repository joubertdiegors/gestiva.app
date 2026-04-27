from django import template

from procurement.utils import format_eur


register = template.Library()


@register.filter(name="eur")
def eur(value):
    return format_eur(value)

