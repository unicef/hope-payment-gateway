# Process

At the moment PG supports Western Union and MoneyGram API integration.

## HOPE send data to PG

HOPE creates a Payment Instruction in PG sending information shared among Payment Records:

- HOPE id
- HOPE code
- destination currency
- business area code
- delivery mechanism
- creator email

Then HOPE creates related Payment Records based on the account:

- HOPE id
- HOPE code
- first name
- last name
- full name
- phone_no
- amount
- destination currency

Moreover, based on the account type, delivery mechanism and country, additional information is sent (e.g. account_number, swift, etc..)


## Linkage to PG models

Based on the Payment Instruction business area code linkage to office is added.

When sending the data to the FSP at runtime the configuration is retrieved using:

- config key / business area
- financial service provider
- delivery mechanism
- country (optional)

In this configuration we can set the required fields for the configuration and additional information such as:

- destination_country
- origination_currency
- counter_id (for Western Union)
- identifier (for Western Union)
- agent_partner_id (for MoneyGram)
- service_provider_routing_code (for MoneyGram)
- service_provider_code (for MoneyGram)

## Data sent to FSP

There's a periodic task running for each FSP takes Ready Payment Instructions and iterates on all Payment Records sending the transactions to the FSP.
If transaction is successful the payment record status is set to Sent to FSP and FSP codes are stored in fsp_code and auth_code.

Western Union and MoneyGram work with push notification which update the status of the Payment Records.
Moreover, we have the possibility to query the status for each Payment Record in the admin.


## HOPE updates data from PG

HOPE request to Payment Plans in:

- status Accepted
- flag sent_to_pg
- payment channel set as API

and related Payment Record which:

- status: pending, sent_to_pg, sent_to_fsp

## Collecting payment records

`hope_payment_gateway.apps.gateway.tasks.collect_payment_records` returns the primary keys of the
Payment Records matching the arguments it is given:

    collect_payment_records(status=PaymentRecordState.PENDING, instruction=123)

Every argument narrows the records to select and is ignored when `None`, so calling the task without
arguments collects every payment record. The supported arguments are:

- `ids`: the Payment Record primary keys
- `status`: a single `PaymentRecordState` or a collection of them
- `office`: the Office primary key of the parent Payment Instruction
- `instruction`: the Payment Instruction primary key

The task returns the record ids so that callers can chain further processing on them. It is meant to
be scheduled through django-celery-beat: create a `PeriodicTask` in the admin pointing at
`hope_payment_gateway.apps.gateway.tasks.collect_payment_records`, with an hourly `IntervalSchedule`
as a sensible default, and optionally add arguments in the `args`/`kwargs` fields. The same arguments
can be passed to an `AsyncJob`, whose `config` maps straight onto them.


## Resync

It is possible to resync with the following script, but we're working on a django button to resync Payment Plan or a single Payment Record.

    pp = PaymentPlan.objects.get(unicef_id="PP-7050-24-00000081")
    pp.eligible_payments.update(status="Pending")
    periodic_sync_payment_gateway_records.delay()
