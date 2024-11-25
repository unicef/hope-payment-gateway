# MoneyGram

When the Payment Plan is ready, PG starts sending data to MoneyGram using REST API.

## Transactions support

### WILL_CALL - Cash in Hand

###  DIRECT_TO_ACCT - Wallets (aka Mobile Money)

### BANK_DEPOSIT - Bank Transfer

moreover are available other transaction types
- WILLCALL_TO
- 2_HOUR
- OVERNIGHT
- OVERNIGHT2ANY
- 24_HOUR
- CARD_DEPOSIT
- HOME_DELIVERY

Once MoneyGram delivers the money to beneficiaries it calls PG api through Webhooks. 


## PG / WU integration

-  PG -> MG: Authentication is performed using rest API and credentials
- MG -> PG: Is done through webhooks and Digital Signature Validation
<https://developer.moneygram.com/moneygram-developer/recipes/webhook-digital-signature-verification>
<https://developer.moneygram.com/moneygram-developer/docs/security>


## Send Money

Payment Gateway creates batches of transactions (maximum 10.000 per hour) to send to WU.
For each transaction, PG calls first the SendMoneyValidation service and then the SendMoneyStore.

## Receive Notification

Western Union calls PG endpoint in order to notify that money has been received by the beneficiary, then PG responds with an acknowledge to Western Union, to confirm the status of the operation:

- SUCCESS
- REFUND
- CANCEL
- REJECT

When Payment Plan is set as ready, PG starts sending data to Western Union though SOAP Requests.

Transactions support:

- Money in Minutes (aka Cash over the counter)
- Wallets (aka Mobile Money)
