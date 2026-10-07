FLAGS = {
    "ENABLE_STREAMING": [{"condition": "boolean", "value": False}],
    # Western Union reconciliation: on by default (the payout amount comes from
    # the notification). List an office code here to turn it off for that office,
    # which makes the notification's payment record payload amount be used instead.
    "WESTERN_UNION_RECONCILIATION_AMOUNT_ON": [{"condition": "office not in", "value": []}],
}
