# Workflow

## Create Transaction

Payment Gateway creates batches of transactions (maximum 10.000 per hour) to send to WU.
For each transaction, PG calls first the SendMoneyValidation service and then the SendMoneyStore.

## Receive Notification

Western Union calls PG endpoint in order to notify that money has been received by the beneficiary, then PG responds with an acknowledgment to Western Union, to confirm the status of the operation:

- SUCCESS
- REFUND
- CANCEL
- REJECT

When the Payment Plan is set as ready, PG starts sending data to Western Union though SOAP Requests.

