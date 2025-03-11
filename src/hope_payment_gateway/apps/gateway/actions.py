import collections
import csv
import datetime
import itertools
from typing import Iterable

from adminactions.api import Echo, csv_options_default
from adminactions.export import base_export
from adminactions.forms import CSVConfigForm
from constance import config
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.admin import helpers
from django.http import HttpResponse, StreamingHttpResponse
from django.shortcuts import redirect, render
from django.template import Context, Template
from django.utils import dateformat
from django.utils.encoding import smart_str
from django.utils.timezone import get_default_timezone
from django.utils.translation import gettext_lazy as _

from hope_payment_gateway.apps.fsp.moneygram.tasks import moneygram_update
from hope_payment_gateway.apps.fsp.western_union.api.client import WesternUnionClient
from hope_payment_gateway.apps.gateway.templatetags.payment import clean_value


class ActionForm(forms.Form):
    _selected_action = forms.CharField(widget=forms.MultipleHiddenInput)
    action = forms.CharField(label="", required=True, initial="", widget=forms.HiddenInput())


class RefundForm(ActionForm):
    REFUND_CHOICES = (
        ("INCORRECT_AMT", "Incorrect Amount"),
        ("TECH_PROB", "Technical Problem"),
        ("DUP_TRAN", "Duplicate Transaction"),
        ("NO_PICKUP", "No Pickup Available"),
        ("WRONG_CRNCY", "Wrong Country"),
        ("WRONG_CNTRY", "Wrong Currency"),
    )
    reason = forms.ChoiceField(choices=REFUND_CHOICES)


class TemplateExportForm(CSVConfigForm):
    _selected_action = forms.CharField(widget=forms.MultipleHiddenInput)
    select_across = forms.BooleanField(
        label="",
        required=False,
        initial=0,
        widget=forms.HiddenInput({"class": "select-across"}),
    )
    action = forms.CharField(label="", required=True, initial="", widget=forms.HiddenInput())

    header = forms.HiddenInput()
    columns = forms.CharField(
        widget=forms.Textarea,
        required=True,
        help_text="one line for each field to export",
    )

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data["header"] = [value.split("#")[0] for value in self.cleaned_data["columns"].split("\r\n")]
        cleaned_data["columns"] = [value.split("#")[-1] for value in self.cleaned_data["columns"].split("\r\n")]
        return cleaned_data


def export_as_template_impl(  # noqa
    queryset,
    fields=None,
    header=None,
    filename=None,
    options=None,
    out=None,
    modeladmin=None,
):
    """Export a queryset as csv from a queryset with the given fields.

    :param queryset: queryset to export
    :param fields: list of fields names to export. None for all fields
    :param header: if True, the exported file will have the first row as column names
    :param filename: name of the filename
    :param options: CSVOptions() instance or none
    :param: out: object that implements File protocol. HttpResponse if None.

    :return: HttpResponse instance
    """
    streaming_enabled = getattr(settings, "ADMINACTIONS_STREAM_CSV", False)
    if out is None:
        if streaming_enabled:
            response_class = StreamingHttpResponse
        else:
            response_class = HttpResponse

        if filename is None:
            filename = "%s.csv" % queryset.model._meta.verbose_name_plural.lower().replace(" ", "_")

        response = response_class(content_type="text/csv")
        response["Content-Disposition"] = ('attachment;filename="%s"' % filename).encode("us-ascii", "replace")
    else:
        response = out

    config = csv_options_default.copy()
    if options:
        config.update(options)

    templates = [Template(template) for template in fields]
    buffer_object = Echo() if streaming_enabled else response

    dialect = config.get("dialect", None)
    if dialect is not None:
        writer = csv.writer(buffer_object, dialect=dialect)
    else:
        writer = csv.writer(
            buffer_object,
            escapechar=config["escapechar"],
            delimiter=str(config["delimiter"]),
            quotechar=str(config["quotechar"]),
            quoting=int(config["quoting"]),
        )

    settingstime_zone = get_default_timezone()

    def yield_header():
        if bool(header):
            if isinstance(header, Iterable):
                yield writer.writerow([clean_value(hd) for hd in header])
            else:
                yield writer.writerow([clean_value(fd) for fd in fields])
        yield ""

    def yield_rows():
        for obj in queryset:
            row = []
            context = Context({"obj": obj})
            for template in templates:
                value = template.render(context)
                if isinstance(value, datetime.datetime):
                    try:
                        value = dateformat.format(
                            value.astimezone(settingstime_zone),
                            config["datetime_format"],
                        )
                    except ValueError:
                        # astimezone() cannot be applied to a naive datetime
                        value = dateformat.format(value, config["datetime_format"])
                elif isinstance(value, datetime.date):
                    value = dateformat.format(value, config["date_format"])
                elif isinstance(value, datetime.time):
                    value = dateformat.format(value, config["time_format"])
                row.append(smart_str(value))
            yield writer.writerow(row)

    if streaming_enabled:
        content_attr = "content" if (StreamingHttpResponse is HttpResponse) else "streaming_content"
        setattr(response, content_attr, itertools.chain(yield_header(), yield_rows()))
    else:
        collections.deque(itertools.chain(yield_header(), yield_rows()), maxlen=0)

    return response


def export_as_template(modeladmin, request, queryset):
    if hasattr(modeladmin, "get_template_export_form"):
        form_class = modeladmin.get_template_export_form(request, "csv") or TemplateExportForm
    else:
        form_class = TemplateExportForm
    return base_export(
        modeladmin,
        request,
        queryset,
        impl=export_as_template_impl,
        name="export_as_template",
        action_short_description=export_as_template.short_description,
        title="%s (%s)"
        % (
            export_as_template.short_description.capitalize(),
            modeladmin.opts.verbose_name_plural,
        ),
        template="payment_instruction/export.html",
        form_class=form_class,
    )


export_as_template.short_description = "Export as Template"


def moneygram_update_status(modeladmin, request, queryset):
    qs = queryset.filter(parent__fsp__vendor_number=config.MONEYGRAM_VENDOR_NUMBER)
    messages.info(request, _(f"Updating {qs.count()}"))
    moneygram_update(qs.values_list("id", flat=True))


def moneygram_refund(modeladmin, request, queryset):
    qs = queryset.filter(parent__fsp__vendor_number=config.MONEYGRAM_VENDOR_NUMBER, fsp_code__isnull=False)
    moneygram_update(qs.values_list("id", flat=True))

    opts = modeladmin.model._meta
    perm = f"{opts.app_label}.can_cancel_transaction"
    if not request.user.has_perm(perm):
        messages.error(request, _("Sorry you do not have rights to execute this action"))
        return None

    initial = {
        "_selected_action": request.POST.getlist(helpers.ACTION_CHECKBOX_NAME),
        "select_across": request.POST.get("select_across") == "1",
        "action": "moneygram_refund",
    }

    if "apply" in request.POST:
        form = RefundForm(request.POST, initial=initial)
        if form.is_valid():
            reason = form.cleaned_data["reason"]
            for obj in qs:
                obj.payload.update({"refuse_reason_code": reason})
                obj.save()
                WesternUnionClient().refund(obj.fsp_code, obj.extra_data)
            messages.info(request, _(f"Updating {qs.count()}"))
        return redirect("admin:gateway_paymentrecord_changelist")

    initial.update({"_validate": 1})

    form = RefundForm(initial=initial)
    admin_form = helpers.AdminForm(form, modeladmin.get_fieldsets(request), {}, [], model_admin=modeladmin)
    ctx = {
        "title": "MoneyGram: Refund",
        "opts": opts,
        "app_label": modeladmin.model._meta.app_label,
        "form": form,
        "selection": queryset,
        "adminform": admin_form,
    }
    ctx.update(modeladmin.admin_site.each_context(request))
    return render(request, "admin/gateway/refund.html", ctx)


moneygram_update_status.short_description = "MoneyGram: update status"
moneygram_refund.short_description = "MoneyGram: mass refund"
