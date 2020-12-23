from typing import Union
import pandas as pd
from .schemas import DefaultOperation as DTS
from ..marketdata.classifiers import classifier


class Operation:
    def __init__(self, setup:Union[DTS,]):
        self.setup = setup
        self.current_result = self.get_last_result()
    
    def refresh_current_result(self, classifier_result:pd.core.frame.DataFrame, reset=False):
        old_result = self.current_result

        quote = self.setup.market.quote_symbol
        base = self.setup.market.base_symbol

        self.current_result = self.current_result.append(classifier_result, ignore_index=True)
        
        if reset:
            quote_amount = 0.0
            base_amount = self.setup.initial_base_amount
        
        else:
            quote_amount = old_result[quote]
            base_amount = old_result[base]

        self.current_result[quote] = quote_amount
        self.current_result[base] = base_amount
    

    def save_current_result(self) -> bool:
        pass
    
    def get_last_result(self) -> pd.core.frame.DataFrame:
        return pd.DataFrame()


class OrderHandler:
    def __init__(self, operation:Operation):
        self.operation = operation

class DefaultTrader:
    def __init__(self, operation=Operation(setup=DTS())):
        self.setup = operation.setup
        self.classifier = classifier(
            self.setup.classifier_name,
            self.setup.market,
            self.setup.time_frame,
            setup=self.setup.classifier_setup,
        )
        self.classifier.backtesting = self.setup.backtesting
        self.order_handler = OrderHandler(operation)
        self.now = ""

    def _start(self):
        pass
    
    def _proceed_analysis_and_order(self):
        self.result = self.classifier.restult_at(desired_datetime=self.now)

    def _get_ready_to_repeat(self):
        pass
    
    def run(self):
        self._start()
        while True:
            self._proceed_analysis_and_order()
            self._get_ready_to_repeat()
        #return self.classifier.restult_at(desired_datetime="2017-11-08 10:00:00")
