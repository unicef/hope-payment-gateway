from typing import Any

from flags.conditions import register


@register("office not in")  # type: ignore[untyped-decorator]
def office_not_in(office_codes: Any, office: Any = None, **kwargs: Any) -> bool:
    """Enable the flag unless the office is listed in the condition value.

    The value is the list of office codes the flag is turned **off** for. An
    office that is not listed keeps the default behaviour, and so does a
    payment record without an office.
    """
    excluded = office_codes if isinstance(office_codes, (list, tuple, set)) else [office_codes]
    if office is None:
        return True
    identifiers = {str(office.code), str(office.pk)}
    return identifiers.isdisjoint(str(code) for code in excluded)
