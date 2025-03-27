# Statuses

## BIS003 = PAID -CASH ONLY

This refers to the MTCNs that have been picked up at a location in Cash.
It does not apply to APN.  


## BIS005 = CANCEL

BIS005 occurs when: Partner performs a cancellation via API, CSC receives a call to cancel or compliance cancels BEFORE settlement. No funds whatsoever are exchanged between the organizations and transaction appears in the settlement file, not in the recap report.
CSC receives a call to cancel after settlement has occurred. This results in a BIS005 Cancel notification. Principal and fees are returned. Transaction appears both in settlement file and recap report.  


## BIS006 with reason code any other than AGE = REFUND

It is not expected that UNICEF receives BIS006 notifications with reason code other than AGE.
BIS006 with reason code AGE (refunded due to aging) = PURGED
This refers to Wester Union system-initiated cancellations or refunds (depending on partner settlement) of unpaid cash MTCNs.
Purge time is set up per client id/account level from 1 to 999 days. A standard purge time is 30 days.
It is WU policy to do a partial refund (we keep fee) on purged payments. This means:
Settle on Send clients get principal only back
Settle on Pay clients are charged a fee upon purge.
There is an exception scenario whereby a transaction that falls in a compliance queue and is never picked up is excluded from the purge process.  The Accounting team should have a process to look at any available MTCNs from Quick Cash accounts that are in “will call (this means available in Western Union terminology) and manually take any required action (for example if the transaction falls in OFAC, funds are held, reported etc)


## BIS0011 = APN REJECT  

This refers to APN MTCNs that are either:
immediately rejected (prior to settlement) by the mobile wallet partner. This results in no funds being exchanged.
delayed-rejected (after settlement) by the mobile wallet partner. This results in a full refund to the partner.
From a notification perspective, partner will get the same notification “APN REJECT BIS0011” for both immediate and delay, even though settlement action may be different.
If BIS0011 (APN REJECT) is received after BIS0012 (APN DELIVED)  for the same MTCN, after settlement,  the partner gets a refund
If BIS0011 (APN REJECT) is received after BIS0012 (APN DELIVED)  for the same MTCN, before settlement,  no funds are exchanged
If BIS0011 (APN REJECT) is received by itself – not after BIS0012 - after settlement,  the partner gets a refund
If BIS0011 (APN REJECT) is received by itself – not after BIS0012- , before settlement,  no funds are exchanged.
   

## BIS0012 = APN DELIVERED

This refers to APN MTCNs that are marked PAID in the system
It does not automatically implied funds have been delivered / settled with Wallet.  
