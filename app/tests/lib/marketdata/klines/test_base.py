# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=too-few-public-methods

from src.lib.marketdata.klines.base import GetInputSanitizer


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
