from django import template

register = template.Library()


@register.filter
def clean_value(value: str) -> str:
    return (
        value.replace(".", " ")
        .replace("_", " ")
        .replace("{", "")
        .replace("}", "")
        .replace("obj", "")
        .replace("|", ": ")
    )
