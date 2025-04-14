# Western Union

When the Payment Plan is ready, PG starts sending data to Western Union though SOAP API Requests.

## Transactions support

- Money in Minutes (aka Cash by FSP)
- Wallet (aka Mobile Money)


## PG / WU integration

- PG -> WU: Authentication is performed through use of certificates
- WU -> PG: Is done through whitelist of IPs and Basic Authentication


## Metadata DAS

- Country/Currency
- Origination and Destination Currency
- Destination Currency
- Delivery Services
- Delivery Option Template
