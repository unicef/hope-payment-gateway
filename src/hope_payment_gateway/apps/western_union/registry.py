from strategy_field.registry import Registry


class FSPProcessor:
    def __init__(self, fsp):
        self.fsp = fsp

    def label(self) -> str:
        return self.__class__.__name__

    def notify(self):
        pass


registry = Registry(FSPProcessor, label_attribute="label")


class DefaultProcessor(FSPProcessor):
    pass
