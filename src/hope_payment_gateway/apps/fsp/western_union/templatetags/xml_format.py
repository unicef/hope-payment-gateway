from defusedxml.minidom import parseString
from django import template

register = template.Library()


@register.simple_tag
def display_xml(xml):
    return parseString(xml).toprettyxml()
