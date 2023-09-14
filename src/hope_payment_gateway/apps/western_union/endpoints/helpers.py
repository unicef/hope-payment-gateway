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
        leaf = path[-2]
        for key in path[:-2]:
            if key not in cursor:
                raise Exception(f"wrong structure: {cursor} should not be a leaf")
            cursor = cursor[key]
        if value is None:
            assert cursor[leaf]
        elif isinstance(value, list):
            assert cursor[leaf]
            assert cursor[leaf] in value
        else:
            cursor[leaf] = value
    return payload
