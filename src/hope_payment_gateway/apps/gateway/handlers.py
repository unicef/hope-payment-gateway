from .forms import MobileMoneyForm
from .registry import DeliveryMechanismProcessor, FSPProcessor


class CSVExportStrategy(FSPProcessor):

    def export(self):
        pass


class MobileMoneyProcessor(DeliveryMechanismProcessor):

    def get_form(self):
        return MobileMoneyForm()
