class FSPClient:
    def create_transaction(self, base_payload, update):
        raise NotImplementedError

    def query_status(self, transaction_id, update):
        raise NotImplementedError

    def refund(self, transaction_id, base_payload):
        raise NotImplementedError
