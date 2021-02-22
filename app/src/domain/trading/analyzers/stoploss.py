class StopTrailing3T:
    def __init__(self, operation):
        self.operation = operation
        self.setup = Deserialize(name="setup").from_json(operation.setup)
        self.klines_getter = klines_getter(
            market=operation.market,
            time_frame=self.setup.classifier_setup.time_frame,
            backtesting=self.setup.backtesting.is_on,
        )
        self.first_trigger = self.setup.classifier_setup.first_trigger
        self.second_trigger = self.setup.classifier_setup.second_trigger
        self.third_trigger = self.setup.classifier_setup.third_trigger
        self.update_target_if = self.setup.classifier_setup.update_target_if
        self.data = pd.DataFrame()
        self.result = pd.DataFrame()
        self.now: int = None

    def number_of_samples(self):
        return max(
            self.first_trigger.treshold.n_measurements,
            self.second_trigger.treshold.n_measurements,
            self.third_trigger.treshold.n_measurements,
            self.update_target_if.treshold.n_measurements,
        )

    def prepare_data(self, desired_datetime: DateTimeType) -> None:
        self.data = self.klines_getter.get(
            until=desired_datetime, number_of_candles=self.number_of_samples()
        )
        self.data.apply_indicator.price_from_kline(
            price_metrics=self.setup.classifier_setup.price_metric
        )
        self.result = pd.DataFrame()
        self.result = self.result.append(self.data[-1:], ignore_index=True)
        self.result["Side"] = self.operation.position.side

    def _are_valid(self, data: pd.core.frame.DataFrame) -> bool:
        enter_time = self.operation.position.timestamp
        data.KlinesDateTime.from_human_readable_to_timestamp()
        first_open_time = data.Open_time.head(1).item()
        return bool(first_open_time >= enter_time)

    def _update_reference_price(self) -> float:
        trigger = self.update_target_if
        slice_length = trigger.treshold.n_measurements
        sliced_data = self.data[-slice_length:]
        exit_reference_price = self.operation.position.exit_reference_price
        price_metrics = self.setup.classifier_setup.price_metrics

        positive_found_column = "Update_reference_n"
        self.result[positive_found_column] = None

        if self._are_valid(sliced_data):
            positives_to_trigger = trigger.treshold.n_positives
            update = False
            if self.operation.position.side == "Long":
                new_reference = (1 + trigger.rate / 100) * exit_reference_price

                filter_condition = (
                    sliced_data.loc[:, "Price_{}".format(price_metrics)]
                    >= new_reference
                )
            if self.operation.position.side == "Short":
                new_reference = (1 - trigger.rate / 100) * exit_reference_price

                filter_condition = (
                    sliced_data.loc[:, "Price_{}".format(price_metrics)]
                    <= new_reference
                )
            positive_found = len(sliced_data[filter_condition])
            self.result[positive_found_column] = positive_found
            update = bool(positive_found >= positives_to_trigger)

            if update:
                self.operation.position.update(
                    exit_reference_price=new_reference
                )

    def _check_trigger(self, name: str):
        trigger = getattr(self, "{}_trigger".format(name))
        slice_length = trigger.treshold.n_measurements
        sliced_data = self.data[-slice_length:]
        exit_reference_price = self.operation.position.exit_reference_price
        price_metrics = self.setup.classifier_setup.price_metrics

        positive_found_column = ("{}_trigger_n".format(name)).capitalize()
        self.result[positive_found_column] = None

        if self._are_valid(sliced_data):
            positives_to_trigger = trigger.treshold.n_positives

            if self.operation.position.side == "Long":
                exit_price = (1 - trigger.rate / 100) * exit_reference_price
                filter_condition = (
                    sliced_data.loc[:, "Price_{}".format(price_metrics)]
                    <= exit_price
                )
            elif self.operation.position.side == "Short":
                exit_price = (1 + trigger.rate / 100) * exit_reference_price
                filter_condition = (
                    sliced_data.loc[:, "Price_{}".format(price_metrics)]
                    >= exit_price
                )
            positive_found = len(sliced_data[filter_condition])
            self.result[positive_found_column] = positive_found
            return bool(positive_found >= positives_to_trigger)
        return False

    def result_at(self, desired_datetime: int) -> pd.core.frame.DataFrame:
        _stop = list()
        self.now = desired_datetime
        self.prepare_data(desired_datetime)
        for name in ["first", "second", "third"]:
            _stop.append(self._check_trigger(name))

        hit_stop = bool(True in _stop)
        if hit_stop:
            self.result.Side = "Zeroed"
        self._update_reference_price()
        return self.result()

    def time_until_next_closed_candle(self):
        return time_until_next_closed_candle(
            time_frame=self.setup.time_frame,
            current_open_time=self.result.Open_time.tail(1).item(),
            now=self.now,
        )

    def time_frame_total_seconds(self):
        return seconds_in(self.setup.time_frame)

class StopLoss:
    def __init__(self, operation: Operation):
        self.operation = operation
        self.step = 60

    def is_activated(self) -> bool:
        pass

    def execution_pipeline(self, at_time:int):
        print(at_time)
        pass