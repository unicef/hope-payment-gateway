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
