import pytest

from hope_payment_gateway.apps.fsp.utils import (
    ascii_name,
    extrapolate_errors,
    get_account_field,
    get_phone_number,
)


def test_get_phone_number_valid():
    phone_number, country_code = get_phone_number("+34600123456")
    assert phone_number == 600123456
    assert country_code == 34


def test_get_phone_number_invalid():
    phone_number, country_code = get_phone_number("invalid")
    assert phone_number == "invalid"
    assert country_code is None


def test_get_account_field():
    payload = {"account": {"field1": "value1", "field2": "value2"}}
    assert get_account_field(payload, "field1") == "value1"
    assert get_account_field(payload, "field3", default="default") == "default"
    assert get_account_field({}, "field1") is None


def test_extrapolate_errors_with_errors_and_offending_fields():
    data = {
        "errors": [
            {
                "message": "Invalid input",
                "code": "INVALID",
                "offendingFields": [{"field": "amount"}, {"field": "currency"}],
            }
        ]
    }
    expected = ["Invalid input (INVALID)", "Field: amount", "Field: currency"]
    assert extrapolate_errors(data) == expected


def test_extrapolate_errors_with_multiple_errors():
    data = {"errors": [{"message": "First error", "code": "ERROR1"}, {"message": "Second error", "code": "ERROR2"}]}
    expected = ["First error (ERROR1)", "Second error (ERROR2)"]
    assert extrapolate_errors(data) == expected


def test_extrapolate_errors_with_single_error():
    data = {"error": "Something went wrong", "message": "Detailed error message"}
    expected = ["Detailed error message"]
    assert extrapolate_errors(data) == expected


def test_extrapolate_errors_with_error_only():
    data = {"error": "Something went wrong"}
    expected = ["Something went wrong"]
    assert extrapolate_errors(data) == expected


def test_extrapolate_errors_with_empty_data():
    data = {}
    expected = ["Error"]
    assert extrapolate_errors(data) == expected


def test_extrapolate_errors_with_invalid_data():
    data = {"some_key": "some_value"}
    expected = ["Error"]
    assert extrapolate_errors(data) == expected


@pytest.mark.parametrize(
    ("input_name", "expected"),
    [
        ("Jose", "Jose"),
        ("José", "Jose"),
        ("François", "Francois"),
        ("Über", "Uber"),
        ("Ça va", "Ca va"),
        ("Ñoño", "Nono"),
        ("Müller", "Muller"),
        ("naïve", "naive"),
        ("", ""),
        ("Alice", "Alice"),
        ("O'Connor", "OConnor"),
    ],
)
def test_ascii_name(input_name, expected):
    assert ascii_name(input_name) == expected
