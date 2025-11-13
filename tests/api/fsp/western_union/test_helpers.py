from hope_payment_gateway.api.western_union.utils import analyze_node


def test_analyze_node():
    template = [
        {
            "house": {"rooms": 5, "zone": ["A", "B", "C"], "price": None},
            "car": {"eur": ["1", "2", "3", "4", "5"]},
        }
    ]
    template_list = analyze_node(template)
    assert template_list == [
        ["house", "rooms", 5],
        ["house", "zone", ["A", "B", "C"]],
        ["house", "price", None],
        ["car", "eur", ["1", "2", "3", "4", "5"]],
    ]
