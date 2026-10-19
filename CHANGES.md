1.22.0
======
* Admin: Render the `JSONField`s declared read-only by an admin (e.g. payment record `fsp_data`, `extra_data`) read-only and pretty-printed, automatically and without any per-field wiring: they are excluded from the change form and shown as an indented JSON tree (`<pre>`), so they can no longer be edited by mistake. `JSONField`s that are not read-only (e.g. payment record `payload`) remain editable with the JSON editor widget
* Core: Raised the default `DATA_UPLOAD_MAX_MEMORY_SIZE` from 5 MB (`5242880`) to 10 MB (`10485760`) so larger request bodies are accepted. It stays overridable through the `DATA_UPLOAD_MAX_MEMORY_SIZE` environment setting
* Core: Build the CSP Azure blob origin from the staticfiles storage `account_name` (e.g. `https://myaccount.blob.core.windows.net`) instead of always allowing `https://*.blob.core.windows.net`; deployments without an `account_name` keep the previous wildcard
* Security: Added explicit least-privilege `permissions` blocks to the GitHub Actions workflows (read-only by default, with `issues: write` / `pull-requests: write` granted only to the stale-issues workflow)
* Security: Log `TransitionNotAllowed`, invalid-request and validation failures server-side (`logger.warning`) before returning the client-facing `status_error` / `invalid_request` / `validation_error` bodies on the payment instruction, payment record and NIS webhook endpoints. The response shape is unchanged, but the failures are now traceable in logs, and the intentional client-facing error details are annotated for CodeQL
* Western Union: Made send-to-FSP handling idempotent when records are already `TRANSFERRED_TO_FSP` (retry-safe). The client and task utils now treat `NoTransition` as success in that case and continue processing remaining records
* Dependencies: Refreshed the lock file (Django 6.0.9, djangorestframework 3.18.3, django-filter 26.2, social-auth-app-django 7.1, social-auth-core 6.1, newrelic 14, pre-commit 4.7, and friends)


1.21.0
======
* Western Union: Keep MTCNs that start with `0` intact when calling the status and refund APIs. They now use the `auth_code` string (as returned by Western Union) instead of `fsp_data["mtcn"]`, which the NIS notification XML parser stored as an `int` and thus dropped the leading `0`, e.g. `0123456789` became `123456789`. Western Union rejected the follow-up call with `E9389 INVALID MTCN LENGTH. MTCN MUST BE 10 CHARACTERS IN LENGTH`
* Western Union: Return `None` instead of the bare `dict` class as the `response_context` placeholder, and stop parsing the status payload when the upstream call failed. Previously a failed `PayStatus` call made the status update log the nonsensical `Missing key in WU status response: dict['payment_transactions'] is not a generic class` instead of the actual upstream error
* Western Union: Added the `WESTERN_UNION_RECONCILIATION_AMOUNT_ON` django-flags flag (enabled by default). It controls whether a successful NIS notification sets `payout_amount` from the notification's `expected_payout_amount` (flag on) or from the payment record payload `amount` (flag off). The flag is off for the office codes listed in its `office not in` condition value, e.g. `[{"condition": "office not in", "value": ["OFFICE-CODE"]}]`; records without an office keep the default


1.20.1
======
* Western Union: Suppress TypeError when the status response returns a plain string instead of a transaction object


1.20.0
======
* Admin: Added `cancel selected payment records` changelist action (requires the `gateway.can_cancel_records` permission); runs as an `AsyncJob` and only cancels records in `TRANSFERRED_TO_FSP` status
* Core: Added missing HTTP security headers (CSP, HSTS, and friends) to all responses
* Core: Hardened session cookie to a 1-day max-age
* AsyncJob: Persist final status locally so SUCCESS/FAILURE survive Celery result expiry


1.19.1
======
* customizable DATA_UPLOAD_MAX_MEMORY_SIZE


1.19.0
======
* Western Union: Status update admin action runs as an async job and requires the `western_union.can_update_status` permission


1.18.2
======
* Western Union: Normalize names to ASCII before sending to WU API (strip accents and non-ASCII characters)


1.18.1
======
* Western Union: Store payout_amount in major currency units (converted from cents) for NIS push notifications and status updates


1.17
===
* Western Union: Added status update admin action (#279)
* Admin: Fix N+1 queries in PaymentInstructionAdmin via select_related (#280)
* Admin: Fix N+1 queries in admin classes via select_related (#281)


1.2
===
* Western Union: Store Transaction date
* Western Union: Expose config and corridor


1.1
===
* Western Union: Fixed service call (wrong env)
* Western Union: Added corridor link


1.0
===

* MoneyGram integration
* Added Account Type model
* Added Office model
* Western Union: added middle name
* Western Union: mass refund
* Added record payout date
* Added Celery boost
* Added Ruff
* Added UV
