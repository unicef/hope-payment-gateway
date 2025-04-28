class FSPClient:
    def create_transaction(self, base_payload, update):
        raise NotImplementedError

    def status(self, transaction_id, update):
        raise NotImplementedError

    def status_update(self, transaction_id, update):
        raise NotImplementedError

    def refund(self, transaction_id, base_payload):
        raise NotImplementedError
