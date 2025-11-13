from hope_payment_gateway.apps.fsp.utils import extrapolate_errors


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
