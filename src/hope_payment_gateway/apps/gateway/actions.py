import collections
import csv
import datetime
import itertools
from typing import Iterable

from django import forms
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse, StreamingHttpResponse
from django.template import Context, Template
from django.utils import dateformat
from django.utils.encoding import smart_str
from django.utils.timezone import get_default_timezone
from django.utils.translation import gettext_lazy as _

from adminactions.api import Echo, csv_options_default
from adminactions.export import base_export
from adminactions.forms import CSVConfigForm
from constance import config

from hope_payment_gateway.apps.fsp.moneygram.tasks import moneygram_update
from hope_payment_gateway.apps.gateway.templatetags.payment import clean_value


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

    config = csv_options_default if options is None else csv_options_default.copy().update(options)

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


moneygram_update_status.short_description = "MoneyGram: update status"
