# Actions

## CANCELLATIONS  

These are UNICEF initiated via the Cancel api call. They can only occur BEFORE settlement.
This means UNICEF gets notified that an MTCN generated was suspended before it settled.
No funds whatsoever are exchanged between the organizations
CSC or our Compliance systems can also initiate a cancellation. UNICEF should get notified regardless
  

## REFUNDS

These are WESTERN UNION initiated via CSC action. They only occur AFTER  settlement. They are not available for UNICEF trigger.
This means UNICEF gets notified that an MTCN generated was suspended AFTER it settled.
As per newly implemented WU policy Full refund (principal and fee) is reversed to UNICEF
CSC or our Compliance systems can also initiate a refund. UNICEF should get notified and corresponding reversal should follow.    


## PURGED  

These are WESTERN UNION SYSTEM initiated automatically and are set for UNICEF to occur at Day 30 after MTCN has been generated, if funds have not been collected.
This means UNICEF gets notified that an MTCN generated was purged AFTER 30 Days and AFTER it settled.
It is WU policy to do PARTIAL  refund (principal ONLY) which is reversed to UNICEF
There is an exception scenario whereby a transaction that falls in a compliance queue and is never picked up is excluded from the purge process.  The Accounting team should have a process to look at any available MTCNs from UNICEF accounts that are in “will call (this means available in Western Union terminology) and manually take any required action (for example if the transaction falls in OFAC, funds are held, reported etc)   

  
## PAID  

This refers to the MTCN that have been picked up or deposited to the wallets (pls refer to the APN Refund project for details on what can occur here if a bank rejects a payment after it has been initially marked as PAID and notification has been sent)  
