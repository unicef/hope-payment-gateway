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

## Resync

It is possible to resync with the following script, but we're working on a django button to resync Payment Plan or a single Payment Record.

    pp = PaymentPlan.objects.get(unicef_id="PP-7050-24-00000081")
    pp.eligible_payments.update(status="Pending")
    periodic_sync_payment_gateway_records.delay()
