# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=too-few-public-methods

from src.lib.marketdata.klines.base import GetInputSanitizer
from src.lib.utils.tools.time_handlers import ParseDateTime


class TestGetInputSanitizer:
    min_ts = 1587999600  # '2020-04-27 15:00:00'
    max_ts = 1593472500  # '2020-06-29 23:15:00'
    sanitizer = GetInputSanitizer(
        sec_time_frame=3600,  # 1h
        min_timestamp=min_ts,
        max_timestamp=max_ts,
    )

    def test_no_inputs(self):
        assert self.sanitizer.sanitize() == (self.min_ts, self.max_ts)

    def test_human_readable_valids_since_and_until(self):
        input_since = "2020-05-01 12:00:00"
        input_until = "2020-06-15 19:55:00"

        expected_output = (
            *(
                ParseDateTime(time_).to_timestamp()
                for time_ in (input_since, input_until)
            ),
        )
        output = self.sanitizer.sanitize(since=input_since, until=input_until)
        assert output == expected_output

    def test_timestamp_invalids_since_and_until(self):
        input_since = self.min_ts - 3600
        input_until = self.max_ts + 3600

        expected_output = self.min_ts, self.max_ts
        output = self.sanitizer.sanitize(since=input_since, until=input_until)
        assert output == expected_output

    def test_since_greater_than_until_but_both_valids(self):
        assert True

    def test_a_valid_since_but_invalid_until(self):
        assert True

    def test_both_valid_until_and_number_samples(self):
        assert True

    def test_a_valid_since_but_invalid_number_samples(self):
        assert True
