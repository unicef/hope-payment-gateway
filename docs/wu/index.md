# Western Union

Once HOPE confirms that Payment Plan is ready, PG starts sending data to Western Union though SOAP Requests.

## Transactions support

- Money in Minutes (aka Cash by FSP)
- Wallets (aka Mobile Money)

Once Western Union deliver the money to beneficiaries it calls PG api through Push Notifications. 


## Metadata DAS

- Country/Currency
- Origination and Destination Currency
- Destination Currency
- Delivery Services
- Delivery Option Template

## PG / WU integration

- PG -> WU: Authentication is performed through use of certificates
- WU -> PG: Is done through withelist of IP and (discussion ongoing) VPN or Basic Authentication


## Send Money

Payment Gateway creates batches of transactions (maximum 10.000 per hour) to send to WU.
For each transaction, PG calls first the SendMoneyValidation service and then the SendMoneyStore.

## Receive Notification

Western Union calls PG endpoint in order to notify that money has been received by the beneficiary, then PG responds with an acknowledge to Western Union, to confirm the status of the operation:

- SUCCESS
- REFUND
- CANCEL
- REJECT

Once HOPE confirms that Payment Plan is ready, PG starts sending data to Western Union though SOAP Requests.

Transactions support:

- Money in Minutes (aka Cash over the counter)
- Wallets (aka Mobile Money)
