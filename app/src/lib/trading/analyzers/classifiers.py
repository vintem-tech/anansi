class Classifier:
    def __init__(self, operation: Operation):
        _setup = operation.operational_setup()
        _payload = PayLoad(
            _setup.market, _setup.classifier, _setup.backtesting
        )
        self._classifier = get_classifier(_payload)
        self.operation = operation
        self.order_handler = OrderHandler(operation)
        self.setup = _setup.classifier.setup
        self.result = pd.DataFrame()
        self.now: int = None

    def time_until_next_closed_candle(self):
        return time_until_next_closed_candle(
            time_frame=self.setup.time_frame,
            current_open_time=self.result.Open_time.tail(1).item(),
            now=self.now,
        )

    def initial_backtesting_now(self) -> int:
        oldest_open_time = self._classifier.klines_getter.oldest_open_time()
        step = (
            self._classifier.number_of_samples()
            * seconds_in(self.setup.time_frame)
        )
        return oldest_open_time + step

    def final_backtesting_now(self) -> int:
        return self._classifier.klines_getter.newest_open_time()

    def _is_a_new_analysis_needed(self):
        last_check = self.operation.last_check.by_classifier_at
        step = seconds_in(self.setup.time_frame)
        return bool(self.now >= last_check + step)

    def execution_pipeline(self, at_time: int):
        self.now = at_time
        if self._is_a_new_analysis_needed():
            self.result = self._classifier.get_restult_at(at_time)
            self.operation.save_result("classifier", self.result)
            self.operation.last_check.update(by_classifier_at=self.now)
            self.order_handler.proceed(at_time, self.result)