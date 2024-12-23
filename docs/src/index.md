# Payment Gateway

The Payment Gateway is a component to perform integration between MIS and FSPs, through web API.
Each FSP can have a different way to interact with the payment gateway with though strategy pattern.


## Repository

> Repo: <https://github.com/unicef/hope-payment-gateway>


## Integration API

PG expose endpoint to accept:

- Payment Plan creation
- Add Records to Payment Plan
- Set Payment Plan ready
- Status of payments given a Payment Plan


## Statues

### Payment Plan

- Draft
- Open
- Ready
- Closed
- Aborted
- Processed

### Payment Record

- Pending
- Transferred to FSP
- Transferred to Beneficiary
- Cancelled
- Refund
- Purged
- Error


### Financial Service Providers

At the moment the Payment Gateway is integrated with:

- Western Union
- MoneyGram
