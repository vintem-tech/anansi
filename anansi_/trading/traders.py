from ..marketdata.classifiers import classifier
from .schemas import DefaultTraderSetup


class Default:
    def __init__(self, setup: DefaultTraderSetup = DefaultTraderSetup()):
        self.setup = setup
        self.classifier = classifier(
            setup.classifier_name,
            setup.market,
            setup.time_frame,
            setup=setup.classifier_setup,
        )
        self.classifier.backtesting = setup.backtesting

    def run(self):
        return self.classifier.restult_at(desired_datetime="2017-11-08 10:00:00")
