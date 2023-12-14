from django import template

register = template.Library()


@register.simple_tag()
def get_value(obj, field, format=None):
    fields = field.split(".")
    for field in fields:
        if "__" in field:
            flex_fields = field.split("__")
            obj = getattr(obj, flex_fields.pop(0), None)
            for ff in flex_fields:
                obj = obj.get(ff)
        else:
            obj = getattr(obj, field, None)
    if format:
        pass
    return obj
