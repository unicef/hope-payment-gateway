# Export

Each Payment Instruction is exported according to an `ExportTemplate`. The template describes how to turn the instruction's Payment Records into a CSV file. The same engine backs two different entry points:

- the **`export_as_template`** admin action (and the per-instruction **Export** button)
- the **`GET /api/rest/payment_instructions/{remote_id}/download/`** REST endpoint

## ExportTemplate

An `ExportTemplate` is bound to an FSP and, optionally, a delivery mechanism, office and country:

| Field | Description |
| --- | --- |
| `config_key` | Arbitrary identifier for the template (unique per FSP) |
| `query` | One line per column, see [Query format](#query-format) |
| `header` | Whether a header row is written (`True` by default) |
| `delimiter` | CSV delimiter (`,` by default) |
| `quotechar` | CSV quote character (`'` by default) |
| `quoting` | CSV quoting strategy: All, Minimal, None or Non Numeric (`All` by default) |
| `escapechar` | CSV escape character (empty by default) |

### How a template is selected

`PaymentInstruction.selected_export` resolves the template for an instruction:

1. If the instruction has a forced `export` FK set, that template is used.
2. Otherwise the **first** `ExportTemplate` matching the instruction's `fsp`, `delivery_mechanism`, `office` and `country` is used, preferring templates that are not office-bound (office `NULL` last).

If no template matches, export fails with "No template found".

### Query format

Each line of `query` is a Django template that is rendered against a single Payment Record as `{{ obj }}`. For example:

```
Record Code#{{ obj.record_code }}
Message#{{ obj.message }}
Amount#{{ obj.payout_amount }}
FSP#{{ obj.parent.fsp.name }}
```

The admin form (`TemplateExportForm`) splits each line on `#`: the part before `#` becomes the column header, the part after `#` becomes the Django template. Render values are coerced to strings; `date`, `time` and `datetime` values are formatted using the configured date/time formats.

When the template list drives the header row itself, header labels are derived from the expressions and cleaned (`{{ obj.record_code }}` becomes `record code`).

## Admin: `export_as_template`

The `PaymentRecordAdmin` changelist exposes the **Export as Template** action (permission `gateway.adminactions_export`).

Workflow:

1. Select one or more Payment Records on the changelist and pick **Export as Template**.
2. The action form lets you edit the columns (one per line in `Header#{{ obj.xxx }}` format) and the CSV options (delimiter, quotechar, quoting, escapechar).
3. On submit, the CSV is returned as an attachment (`text/csv`), named `payment_records.csv` by default.

`PaymentInstructionAdmin` also offers a per-instruction **Export** button (permission `gateway.can_export_records`) that pre-fills the form from the instruction's `selected_export` and exports all of its records.

## REST: download

```
GET /api/rest/payment_instructions/{remote_id}/download/
```

The endpoint does not stream the file. It schedules an asynchronous job that emails the matching CSV attachment to the requesting user.

Auth: the request must be authenticated (token). The authenticated user must have an email address.

### Flow

1. The instruction is resolved by `remote_id`.
2. `selected_export` resolves the export template (see above).
3. An `AsyncJob` (type `STANDARD_TASK`) is created for `export_payment_instruction_to_email`, capturing the instruction and the requester's email.
4. The job is queued and runs in the background: it renders every Payment Record of the instruction using the template's `query`, writes the CSV and emails it as `payment_instruction_{remote_id or pk}.csv`.

### Responses

| Status | Body | When |
| --- | --- | --- |
| `202` | `{"message": "Export scheduled", "job_id": <id>}` | Export accepted and queued |
| `400` | `{"status_error": "No template found"}` | No `ExportTemplate` matches the instruction |
| `400` | `{"status_error": "User email is required"}` | The authenticated user has no email |

### Example

```
curl -X GET \
  -H "Authorization: Token <token>" \
  https://<host>/api/rest/payment_instructions/PI-2024-0001/download/
```

```json
{
  "message": "Export scheduled",
  "job_id": 42
}
```
