# Payment Gateway

The Integration between HOPE and any FSP is performed through a middleware service called Payment Gateway (PG).
HOPE sends to the PG information regarding Payments through web API.
Each FSP can have a different way to interact with the payment gateway with though strategy pattern.


## Repository

> Repo: <https://github.com/unicef/hope-payment-gateway>


## HOPE / PG Integration API

PG expose endpoint to accept:

- Payment Plan creation
- Add Records to Payment Plan
- Payment Plan ready
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
- Moneygram
