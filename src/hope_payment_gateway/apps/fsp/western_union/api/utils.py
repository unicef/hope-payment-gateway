from hope_payment_gateway.apps.fsp.exceptions import (
    InvalidChoiceFromCorridorError,
    MissingValueInCorridorError,
    PayloadIncompatibleError,
)


def analyze_node(nodes, partial=None) -> list:
    if partial is None:
        partial = []
    for item in nodes:
        if isinstance(item, dict):
            news = []
            for key, value in item.items():
                biz = analyze_node(
                    [value],
                    partial
                    + [
                        key,
                    ],
                )
                if isinstance(value, dict):
                    news.extend(biz)
                else:
                    news.append(biz)
            return news
        partial.append(item)
    return partial


def integrate_payload(payload, template):
    template_list = analyze_node([template])
    for path in template_list:
        cursor = payload
        value = path[-1]
        leaf = path[-2]
        for key in path[:-2]:
            if key not in cursor:
                raise PayloadIncompatibleError(f"Wrong structure: {key} should not be a leaf")
            cursor = cursor[key]
        if value is None:
            if cursor[leaf] is None:
                raise MissingValueInCorridorError(f"Missing Value in Corridor {leaf}")
        elif isinstance(value, list):
            val = cursor[leaf] or "-"
            if val is None or val not in value:
                raise InvalidChoiceFromCorridorError(f"Invalid Choice {leaf} for {val}")
        else:
            cursor[leaf] = value
    return payload
