# Export

Each Payment Instruction is exported according to an `ExportTemplate`. The template
describes how to turn the instruction's Payment Records into a CSV file. The same
engine backs two different entry points:

- the **`export_as_template`** admin action (and the per-instruction **Export** button)
- the **`GET /api/rest/payment_instructions/{remote_id}/download/`** REST endpoint

## ExportTemplate

An `ExportTemplate` is bound to an FSP and, optionally, a delivery mechanism,
office and country:

| Field | Description |
| --- | --- |
| `fsp` | Financial Service Provider the template applies to (required) |
| `delivery_mechanism` | Delivery mechanism the template applies to (required) |
| `office` | Office the template applies to (optional; `NULL` = not office-bound) |
| `country` | Country the template applies to (optional) |
| `config_key` | Arbitrary identifier for the template (unique per FSP) |
| `strategy` | Optional export strategy registered in `export_registry` |
| `query` | One line per column, see [Query format](#query-format) |
| `header` | Whether a header row is written (`True` by default) |
| `delimiter` | CSV delimiter (`,` by default) |
| `quotechar` | CSV quote character (`'` by default) |
| `quoting` | CSV quoting strategy: All, Minimal, None or Non Numeric (`All` by default) |
| `escapechar` | CSV escape character (empty by default) |

### How a template is selected

`PaymentInstruction.selected_export` resolves the template for an instruction:

1. If the instruction has a forced `export` FK set, that template is used.
2. Otherwise the **first** `ExportTemplate` matching the instruction's `fsp`,
   `delivery_mechanism`, `office` and `country` is used, preferring templates
   that are not office-bound (office `NULL` last, i.e. `ORDER BY office ASC NULLS LAST`).

If no template matches, export fails with "No template found".

### Query format

Each line of `query` is a Django template that is rendered against a single
Payment Record as `{{ obj }}`. The line is split on the first `#`: the part
before `#` becomes the column header, the part after `#` becomes the Django
template.

Example:

```
Record Code#{{ obj.record_code }}
Message#{{ obj.message }}
Amount#{{ obj.payout_amount }}
FSP#{{ obj.parent.fsp.name }}
Status#{{ obj.status }}
```

Render values are coerced to strings. `date`, `time` and `datetime` values are
formatted using the configured date/time formats (`DATETIME_FORMAT`, `DATE_FORMAT`,
`TIME_FORMAT`).

When the template is driven by a list of expressions without explicit headers,
header labels are derived from the expressions and cleaned
(`{{ obj.record_code }}` becomes `record code`).

Tips:

- Use `{{ obj.parent.xxx }}` to reach fields on the parent Payment Instruction
  (e.g. `{{ obj.parent.fsp.name }}`, `{{ obj.parent.external_code }}`).
- Keep one column per line; blank lines produce empty columns.
- Test the template from the admin **Export** button before relying on the REST
  endpoint, since both use the same engine.

## Admin: `export_as_template`

The `PaymentRecordAdmin` changelist exposes the **Export as Template** action
(permission `gateway.adminactions_export`).

Workflow:

1. Select one or more Payment Records on the changelist and pick
   **Export as Template**.
2. The action form lets you edit the columns (one per line in
   `Header#{{ obj.xxx }}` format) and the CSV options (delimiter, quotechar,
   quoting, escapechar).
3. On submit, the CSV is returned as an attachment (`text/csv`), named
   `payment_records.csv` by default.

`PaymentInstructionAdmin` also offers a per-instruction **Export** button
(permission `gateway.can_export_records`) that pre-fills the form from the
instruction's `selected_export` and exports all of its records.

## REST: download

```
GET /api/rest/payment_instructions/{remote_id}/download/
```

The endpoint does **not** stream the file. It schedules an asynchronous job that
renders the CSV and emails it as an attachment to the requesting user.

### Authentication and permissions

- The request must be authenticated with a token
  (`Authorization: Token <token>`).
- The authenticated user must have an email address; otherwise the request is
  rejected with `400`.
- The token must carry the grants needed to read/manage payment instructions
  (at least `API_READ_ONLY`; upload/manage grants are required for the other
  instruction actions).

### Flow

1. The instruction is resolved by `remote_id` (any string, e.g. a UUID such as
   `edd92c3b-797f-4008-b412-3c064e4a5d6e`).
2. `selected_export` resolves the export template (see above).
3. An `AsyncJob` (type `STANDARD_TASK`) is created for
   `export_payment_instruction_to_email`, capturing the instruction primary key
   and the requester's email.
4. The job is queued and runs in the background: it renders every Payment Record
   of the instruction using the template's `query`, writes the CSV and emails it
   as `payment_instruction_{remote_id or pk}.csv`.

### Responses

| Status | Body | When |
| --- | --- | --- |
| `202` | `{"message": "Export scheduled", "job_id": <id>}` | Export accepted and queued |
| `400` | `{"status_error": "No template found"}` | No `ExportTemplate` matches the instruction |
| `400` | `{"status_error": "User email is required"}` | The authenticated user has no email |
| `404` | — | No Payment Instruction with the given `remote_id` |

### How to use

1. Make sure the Payment Instruction has at least one matching `ExportTemplate`
   (forced via the `export` field or matching FSP/delivery mechanism/office/country).
2. Authenticate with a token whose user has an email address.
3. Issue a `GET` request to the instruction's `download` endpoint using its
   `remote_id`:

   ```
   curl -X GET \
     -H "Authorization: Token <token>" \
     https://<host>/api/rest/payment_instructions/edd92c3b-797f-4008-b412-3c064e4a5d6e/download/
   ```

4. Read the `job_id` from the `202` response and track the asynchronous job
   (via the `AsyncJob` admin/API). The rendered CSV
   (`payment_instruction_{remote_id or pk}.csv`) is emailed to the requesting
   user once the job finishes.

   ```json
   {
     "message": "Export scheduled",
     "job_id": 42
   }
   ```

### Tracking and Troubleshooting

- **"No template found"**: create or fix an `ExportTemplate` for the
  instruction's FSP/delivery mechanism/office/country, or set the instruction's
  forced `export` FK.
- **"User email is required"**: update the requesting user's email address.
- **Job never arrives**: check the `AsyncJob` status (Celery task
  `hope_payment_gateway.apps.core.tasks.sync_job_task`) and the worker logs; a
  missing template raises `ValueError("No template found")` inside the job.
- **Empty CSV**: verify the template's `query` references valid fields on
  `PaymentRecord` (and `parent` for instruction-level fields) and that the
  instruction actually has records.
- **Encoding/quoting issues**: adjust `delimiter`, `quotechar`, `quoting` and
  `escapechar` on the `ExportTemplate` (or via the admin form) and re-run.
yment_gateway.apps.gateway.models.PaymentInstruction.selected_export`
