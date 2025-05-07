from datetime import datetime, date, time
from unittest.mock import patch, MagicMock

import pytest
from constance.test import override_config
from django.conf import settings
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse, StreamingHttpResponse, QueryDict
from django.urls import reverse
from factories import PaymentRecordFactory
from hope_payment_gateway.apps.gateway.actions import (
    TemplateExportForm,
    export_as_template_impl,
    export_as_template,
    moneygram_update_status,
    moneygram_refund,
)
from hope_payment_gateway.apps.gateway.models import PaymentRecord


@pytest.fixture
def request_with_messages(request_factory):
    request = request_factory.post("/")
    middleware = SessionMiddleware(lambda r: None)
    middleware.process_request(request)
    middleware = MessageMiddleware(lambda r: None)
    middleware.process_request(request)
    return request


@pytest.fixture
def sample_queryset():
    from hope_payment_gateway.apps.gateway.models import PaymentRecord

    records = PaymentRecordFactory.create_batch(2)
    return PaymentRecord.objects.filter(id__in=[r.id for r in records])


@pytest.fixture
def request_with_data(request_with_messages, admin_user):
    from django.http import QueryDict

    request_with_messages.user = admin_user
    post_data = QueryDict(mutable=True)
    post_data.update(
        {
            "action": "export_as_template",
            "_selected_action": ["1", "2"],
            "columns": "Record Code#record_code\r\nMessage#message",
            "delimiter": ",",
            "quotechar": '"',
            "quoting": "0",
            "escapechar": "\\",
            "apply": "Export",
        }
    )
    request_with_messages.POST = post_data
    return request_with_messages


@pytest.mark.parametrize(
    ("input_data", "expected_headers", "expected_columns"),
    [
        ("Name#name\r\nAmount#amount\r\nDate#date", ["Name", "Amount", "Date"], ["name", "amount", "date"]),
        ("Single#field", ["Single"], ["field"]),
        ("Empty#\r\nValue#test", ["Empty", "Value"], ["", "test"]),
    ],
)
def test_template_export_form_clean_method(input_data, expected_headers, expected_columns):
    form_data = {
        "columns": input_data,
        "header": "",
        "select_across": "0",
        "action": "export_as_template",
        "_selected_action": "1,2,3",
        "delimiter": ",",
        "quotechar": '"',
        "quoting": "0",
        "escapechar": "\\",
    }
    form = TemplateExportForm(data=form_data)
    assert form.is_valid()
    cleaned_data = form.cleaned_data
    assert cleaned_data["header"] == expected_headers
    assert cleaned_data["columns"] == expected_columns


@pytest.mark.django_db
def test_basic_export(sample_queryset):
    fields = ["{{ obj.record_code }}", "{{ obj.message }}"]
    header = ["Record Code", "Message"]

    response = export_as_template_impl(queryset=sample_queryset, fields=fields, header=header, filename="test.csv")

    assert isinstance(response, HttpResponse)
    assert response["Content-Type"] == "text/csv"
    assert "test.csv" in response["Content-Disposition"]


@pytest.mark.parametrize("streaming_enabled", [True, False])
@pytest.mark.django_db
def test_streaming_export(sample_queryset, streaming_enabled):
    settings.ADMINACTIONS_STREAM_CSV = streaming_enabled
    fields = ["{{ obj.record_code }}"]

    response = export_as_template_impl(
        queryset=sample_queryset, fields=fields, out=None if streaming_enabled else HttpResponse()
    )

    expected_class = StreamingHttpResponse if streaming_enabled else HttpResponse
    assert isinstance(response, expected_class)
    settings.ADMINACTIONS_STREAM_CSV = False


@pytest.mark.django_db
def test_with_custom_options(sample_queryset):
    options = {"delimiter": ";", "quotechar": "'", "quoting": 1, "escapechar": "\\"}

    response = export_as_template_impl(queryset=sample_queryset, fields=["{{ obj.record_code }}"], options=options)

    assert isinstance(response, HttpResponse)


@pytest.mark.parametrize(
    ("field_type", "field_value", "expected_format"),
    [
        ("datetime", datetime(2023, 1, 1, 12, 0), "Y-m-d H:i:s"),
        ("date", date(2023, 1, 1), "Y-m-d"),
        ("time", time(12, 0), "H:i:s"),
    ],
)
@pytest.mark.django_db
def test_datetime_formatting(field_type, field_value, expected_format):
    record = PaymentRecordFactory(record_code=field_value)
    queryset = PaymentRecord.objects.filter(id=record.id)
    fields = ["{{ obj.record_code }}"]

    response = export_as_template_impl(queryset=queryset, fields=fields, options={"datetime_format": expected_format})

    assert isinstance(response, HttpResponse)


@pytest.mark.django_db
def test_with_custom_dialect(sample_queryset):
    from csv import excel_tab

    fields = ["{{ obj.record_code }}", "{{ obj.message }}"]
    header = ["Record Code", "Message"]

    response = export_as_template_impl(
        queryset=sample_queryset, fields=fields, header=header, options={"dialect": excel_tab}
    )

    assert isinstance(response, HttpResponse)
    content = response.content.decode()
    assert "\t" in content


@pytest.mark.django_db
def test_header_generation(sample_queryset):
    fields = ["{{ obj.record_code }}", "{{ obj.message }}"]
    header = ["Record Code", "Message"]

    response = export_as_template_impl(
        queryset=sample_queryset,
        fields=fields,
        header=header,
        options={"delimiter": ",", "quotechar": '"', "quoting": 0, "escapechar": "\\"},
    )

    content = response.content.decode()
    lines = content.split("\n")
    assert lines[0].rstrip("\r") == "Record Code,Message"


@pytest.mark.django_db
def test_header_generation_without_header(sample_queryset):
    fields = ["{{ obj.record_code }}", "{{ obj.message }}"]

    response = export_as_template_impl(
        queryset=sample_queryset,
        fields=fields,
        header=True,
        options={"delimiter": ",", "quotechar": '"', "quoting": 0, "escapechar": "\\"},
    )

    content = response.content.decode()
    lines = content.split("\n")
    assert lines[0].strip() == "record code ,  message"


@pytest.mark.django_db
def test_export_with_valid_form(modeladmin, request_with_data):
    records = PaymentRecordFactory.create_batch(2)
    queryset = PaymentRecord.objects.filter(id__in=[r.id for r in records])

    with patch("hope_payment_gateway.apps.gateway.actions.export_as_template_impl") as mock_impl:
        mock_response = HttpResponse()
        mock_response.status_code = 200
        mock_impl.return_value = mock_response
        with patch("hope_payment_gateway.apps.gateway.actions.TemplateExportForm") as mock_form:
            mock_form.return_value.is_valid.return_value = True
            mock_form.return_value.cleaned_data = {
                "header": ["Record Code", "Message"],
                "columns": ["{{ obj.record_code }}", "{{ obj.message }}"],
            }
            response = export_as_template(modeladmin, request_with_data, queryset)

            assert response.status_code == 200
            mock_impl.assert_called_once()
            call_kwargs = mock_impl.call_args[1]
            assert call_kwargs["fields"] == ["{{ obj.record_code }}", "{{ obj.message }}"]
            assert call_kwargs["header"] == ["Record Code", "Message"]
            assert isinstance(call_kwargs["options"], dict)
            assert call_kwargs["options"]["header"] == ["Record Code", "Message"]
            assert call_kwargs["options"]["columns"] == ["{{ obj.record_code }}", "{{ obj.message }}"]
            assert call_kwargs["modeladmin"] == modeladmin


@pytest.mark.django_db
def test_export_with_custom_form_class(modeladmin, request_with_data):
    class CustomForm(TemplateExportForm):
        pass

    modeladmin.get_template_export_form = MagicMock(return_value=CustomForm)
    records = PaymentRecordFactory.create_batch(2)
    queryset = PaymentRecord.objects.filter(id__in=[r.id for r in records])

    with patch("hope_payment_gateway.apps.gateway.actions.export_as_template_impl") as mock_impl:
        mock_response = HttpResponse()
        mock_response.status_code = 200
        mock_impl.return_value = mock_response
        with patch("hope_payment_gateway.apps.gateway.actions.TemplateExportForm") as mock_form:
            mock_form.return_value.is_valid.return_value = True
            mock_form.return_value.cleaned_data = {
                "header": ["Record Code", "Message"],
                "columns": ["{{ obj.record_code }}", "{{ obj.message }}"],
            }
            response = export_as_template(modeladmin, request_with_data, queryset)

            assert response.status_code == 200
            modeladmin.get_template_export_form.assert_called_once_with(request_with_data, "csv")


@pytest.mark.django_db
def test_export_with_invalid_form(modeladmin, request_with_data):
    post_data = QueryDict(mutable=True)
    post_data.update(
        {
            "action": "export_as_template",
            "_selected_action": ["1", "2"],
            "columns": "",
            "delimiter": ",",
            "quotechar": '"',
            "quoting": "0",
            "escapechar": "\\",
            "apply": "Export",
        }
    )
    request_with_data.POST = post_data
    records = PaymentRecordFactory.create_batch(2)
    queryset = PaymentRecord.objects.filter(id__in=[r.id for r in records])

    with patch("hope_payment_gateway.apps.gateway.actions.export_as_template_impl") as mock_impl:
        with patch("hope_payment_gateway.apps.gateway.actions.TemplateExportForm") as mock_form:
            mock_form.return_value.is_valid.return_value = False
            response = export_as_template(modeladmin, request_with_data, queryset)

            assert response.status_code == 200
            mock_impl.assert_not_called()


@pytest.mark.django_db
def test_export_with_empty_queryset(modeladmin, request_with_data):
    queryset = PaymentRecord.objects.none()

    with patch("hope_payment_gateway.apps.gateway.actions.export_as_template_impl") as mock_impl:
        with patch("hope_payment_gateway.apps.gateway.actions.TemplateExportForm") as mock_form:
            mock_form.return_value.is_valid.return_value = True
            mock_form.return_value.cleaned_data = {
                "header": ["Record Code", "Message"],
                "columns": ["{{ obj.record_code }}", "{{ obj.message }}"],
            }
            with patch("hope_payment_gateway.apps.gateway.actions.base_export") as mock_base_export:
                mock_response = HttpResponse()
                mock_response.status_code = 200
                mock_response.content = b"No records selected"
                mock_base_export.return_value = mock_response
                response = export_as_template(modeladmin, request_with_data, queryset)

                assert response.status_code == 200
                mock_impl.assert_not_called()
                assert "No records selected" in response.content.decode()


@pytest.mark.django_db
def test_export_with_custom_template(modeladmin, request_with_data):
    modeladmin.get_template_export_form = MagicMock(return_value=None)
    records = PaymentRecordFactory.create_batch(2)
    queryset = PaymentRecord.objects.filter(id__in=[r.id for r in records])

    with patch("hope_payment_gateway.apps.gateway.actions.export_as_template_impl") as mock_impl:
        mock_response = HttpResponse()
        mock_response.status_code = 200
        mock_impl.return_value = mock_response
        with patch("hope_payment_gateway.apps.gateway.actions.TemplateExportForm") as mock_form:
            mock_form.return_value.is_valid.return_value = True
            mock_form.return_value.cleaned_data = {
                "header": ["Record Code", "Message"],
                "columns": ["{{ obj.record_code }}", "{{ obj.message }}"],
            }
            with patch("hope_payment_gateway.apps.gateway.actions.base_export") as mock_base_export:
                mock_base_export.return_value = mock_response
                response = export_as_template(modeladmin, request_with_data, queryset)

                assert response.status_code == 200
                mock_base_export.assert_called_once()
                call_args = mock_base_export.call_args[0]
                call_kwargs = mock_base_export.call_args[1]

                assert call_args[0] == modeladmin
                assert call_args[1] == request_with_data
                assert call_args[2] == queryset
                assert call_kwargs["impl"]._mock_name == "export_as_template_impl"
                assert call_kwargs["name"] == "export_as_template"
                assert call_kwargs["action_short_description"] == export_as_template.short_description
                assert call_kwargs["title"] == "%s (%s)" % (
                    export_as_template.short_description.capitalize(),
                    modeladmin.opts.verbose_name_plural,
                )
                assert call_kwargs["template"] == "payment_instruction/export.html"
                assert call_kwargs["form_class"]._mock_name == "TemplateExportForm"


@override_config(MONEYGRAM_VENDOR_NUMBER="67890")
@pytest.mark.django_db
def test_moneygram_update_called(modeladmin, request_with_messages, mg):
    records = PaymentRecordFactory.create_batch(2, parent__fsp=mg)
    record_ids = [record.id for record in records]
    queryset = PaymentRecord.objects.filter(id__in=record_ids).values_list("id", flat=True)

    with patch("hope_payment_gateway.apps.gateway.actions.moneygram_update") as mock_update:
        moneygram_update_status(modeladmin, request_with_messages, queryset)
        mock_update.assert_called_once()


@override_config(MONEYGRAM_VENDOR_NUMBER="67890")
@pytest.mark.django_db
def test_refund_with_permission(modeladmin, request_with_messages, mg):
    records = PaymentRecordFactory.create_batch(2, parent__fsp=mg, fsp_code="TEST123")
    record_ids = [record.id for record in records]
    queryset = PaymentRecord.objects.filter(id__in=record_ids)

    post_data = QueryDict(mutable=True)
    post_data.update(
        {
            "action": "moneygram_refund",
            "_selected_action": [str(r.id) for r in records],
            "select_across": "0",
            "apply": "1",
            "reason": "test_reason",
        }
    )
    request_with_messages.POST = post_data
    request_with_messages.user = MagicMock()
    request_with_messages.user.has_perm.return_value = True

    with patch("hope_payment_gateway.apps.gateway.actions.moneygram_update") as mock_update:
        with patch("hope_payment_gateway.apps.gateway.actions.MoneyGramClient") as mock_client:
            with patch("hope_payment_gateway.apps.gateway.actions.RefundForm") as mock_form:
                mock_form.return_value.is_valid.return_value = True
                mock_form.return_value.cleaned_data = {"reason": "test_reason"}
                mock_client.return_value.refund.return_value = None
                response = moneygram_refund(modeladmin, request_with_messages, queryset)

                mock_update.assert_called_once()

                assert mock_client.return_value.refund.call_count == len(records)

                for record in records:
                    record.refresh_from_db()
                    assert record.payload["refuse_reason_code"] == "test_reason"

                assert response.status_code == 302
                assert response.url == reverse("admin:gateway_paymentrecord_changelist")


@override_config(MONEYGRAM_VENDOR_NUMBER="67890")
@pytest.mark.django_db
def test_refund_without_permission(modeladmin, request_with_messages, mg):
    records = PaymentRecordFactory.create_batch(2, parent__fsp=mg, fsp_code="TEST123")
    record_ids = [record.id for record in records]
    queryset = PaymentRecord.objects.filter(id__in=record_ids)

    post_data = QueryDict(mutable=True)
    post_data.update(
        {
            "action": "moneygram_refund",
            "_selected_action": [str(r.id) for r in records],
            "select_across": "0",
            "apply": "1",
            "reason": "test_reason",
        }
    )
    request_with_messages.POST = post_data
    request_with_messages.user = MagicMock()
    request_with_messages.user.has_perm.return_value = False

    with patch("hope_payment_gateway.apps.gateway.actions.moneygram_update") as mock_update:
        with patch("hope_payment_gateway.apps.gateway.actions.MoneyGramClient") as mock_client:
            response = moneygram_refund(modeladmin, request_with_messages, queryset)

            mock_update.assert_called_once()

            mock_client.return_value.refund.assert_not_called()

            messages = list(request_with_messages._messages)
            assert len(messages) == 1
            assert str(messages[0]) == "Sorry you do not have rights to execute this action"

            assert response is None


@override_config(MONEYGRAM_VENDOR_NUMBER="67890")
@pytest.mark.django_db
def test_refund_with_invalid_form(modeladmin, request_with_messages, mg):
    records = PaymentRecordFactory.create_batch(2, parent__fsp=mg, fsp_code="TEST123")
    record_ids = [record.id for record in records]
    queryset = PaymentRecord.objects.filter(id__in=record_ids)

    post_data = QueryDict(mutable=True)
    post_data.update(
        {"action": "moneygram_refund", "_selected_action": [str(r.id) for r in records], "select_across": "0"}
    )
    request_with_messages.POST = post_data
    request_with_messages.user = MagicMock()
    request_with_messages.user.has_perm.return_value = True

    with patch("hope_payment_gateway.apps.gateway.actions.moneygram_update") as mock_update:
        with patch("hope_payment_gateway.apps.gateway.actions.MoneyGramClient") as mock_client:
            with patch("hope_payment_gateway.apps.gateway.actions.RefundForm") as mock_form:
                with patch("hope_payment_gateway.apps.gateway.actions.helpers") as mock_helpers:
                    with patch("hope_payment_gateway.apps.gateway.actions.render") as mock_render:
                        mock_form_instance = MagicMock()
                        mock_form_instance.is_valid.return_value = False
                        mock_form_instance.errors = {"reason": ["This field is required."]}
                        mock_form.return_value = mock_form_instance

                        mock_admin_form = MagicMock()
                        mock_helpers.AdminForm.return_value = mock_admin_form

                        modeladmin.get_fieldsets.return_value = []

                        modeladmin.admin_site.each_context.return_value = {}

                        mock_response = HttpResponse()
                        mock_response.status_code = 200
                        mock_render.return_value = mock_response

                        mock_update.return_value = None

                        response = moneygram_refund(modeladmin, request_with_messages, queryset)

                        mock_update.assert_called_once()

                        mock_client.return_value.refund.assert_not_called()

                        mock_form.assert_called_once()
                        call_args = mock_form.call_args[1]
                        assert "_validate" in call_args["initial"]
                        assert call_args["initial"]["_validate"] == 1
                        assert call_args["initial"]["select_across"] is False
                        assert call_args["initial"]["action"] == "moneygram_refund"

                        mock_helpers.AdminForm.assert_called_once_with(
                            mock_form_instance, [], {}, [], model_admin=modeladmin
                        )

                        mock_render.assert_called_once()
                        render_args = mock_render.call_args[0]
                        assert render_args[0] == request_with_messages
                        assert render_args[1] == "admin/gateway/refund.html"
                        assert "title" in render_args[2]
                        assert render_args[2]["title"] == "MoneyGram: Refund"
                        assert "form" in render_args[2]
                        assert render_args[2]["form"] == mock_form_instance
                        assert "selection" in render_args[2]
                        assert render_args[2]["selection"] == queryset
                        assert "adminform" in render_args[2]
                        assert render_args[2]["adminform"] == mock_admin_form

                        assert response.status_code == 200
