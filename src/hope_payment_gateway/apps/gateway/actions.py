import collections
import csv
import datetime
import itertools
from typing import List

from django import forms
from django.conf import settings
from django.http import HttpResponse, StreamingHttpResponse
from django.template import Context, Template
from django.utils import dateformat
from django.utils.encoding import smart_str
from django.utils.timezone import get_default_timezone

from adminactions.api import Echo, csv_options_default
from adminactions.export import base_export
from adminactions.forms import CSVConfigForm

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

    columns = forms.CharField(
        widget=forms.Textarea,
        required=True,
        help_text="one line for each field to export",
    )

    # def __init__(self, *args: Any, **kwargs: Any) -> None:
    #     if request := kwargs.pop("request", None):
    #         if is_root(request):
    #             self.base_fields["status"].choices = self.STATUSES_CHOICES + self.STATUSES_ROOT_CHOICES
    #     super().__init__(*args, **kwargs)

    def clean_columns(self) -> List:
        return self.cleaned_data["columns"].split("\r\n")

    # def clean_columns(self, values) -> List:
    #     return values.split("\r\n")


def export_as_template_impl(  # noqa: max-complexity: 20
    queryset,
    fields=None,
    header=None,
    filename=None,
    options=None,
    out=None,
    modeladmin=None,
):  # noqa
    """
        Exports a queryset as csv from a queryset with the given fields.

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

    if options is None:
        config = csv_options_default
    else:
        config = csv_options_default.copy()
        config.update(options)

    templates = [Template(template) for template in fields]

    if streaming_enabled:
        buffer_object = Echo()
    else:
        buffer_object = response

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
            if isinstance(header, (list, tuple)):
                yield writer.writerow([clean_value(header) for header in fields])
            else:
                yield writer.writerow([clean_value(f) for f in fields])
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
