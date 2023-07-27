def analyze_node(nodes, partial=[]):
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
        else:
            partial.append(item)
            return partial


def integrate_payload(payload, template):
    template_list = analyze_node([template])
    for path in template_list:
        cursor = payload
        value = path[-1]
        for key in path[:-1]:
            if key not in cursor:
                cursor[key] = dict()
            if not isinstance(cursor, dict):
                raise Exception(f"wrong structure: {cursor} should not be a leaf")
            cursor = cursor[key]
        if value is None:
            if cursor is None or not cursor:
                raise (Exception(f"missing element {cursor} in {value}"))
        elif isinstance(value, list):
            if cursor not in value:
                raise (Exception(f"invalid choice {cursor} for {path}"))
        else:
            cursor[key] = value
    return payload
