from django import template

register = template.Library()


@register.filter
def clean_value(value):
    return (
        value.replace(".", " ")
        .replace("_", " ")
        .replace("{", "")
        .replace("}", "")
        .replace("obj", "")
        .replace("|", ": ")
    )
