from hope_payment_gateway.apps.western_union.endpoints.helpers import analyze_node


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


# def test_integrate_payload_ok():
#     payload = {
#         "house": {"zone": "A", "price": 10, "color": "RED"},
#         "car": {"eur": "1"},
#     }
#
#     template = {
#         "house": {"zone": ["A", "B", "C"], "price": None, "rooms": 5},
#         "car": {"eur": ["1", "2", "3", "4", "5"]},
#     }
#
#     new_payload = integrate_payload(payload, template)
#
#     assert new_payload == {
#         "house": {"zone": "A", "price": 10, "color": "RED", "rooms": 5},
#         "car": {"eur": "1"},
#     }
