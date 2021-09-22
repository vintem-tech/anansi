"""An abstraction for outgoing messages"""

# pylint: disable=no-name-in-module
# pylint: disable=E1136

from typing import Union  # , Sequence, Optional, List

from pydantic import BaseModel  # , validator

from ..utils.tools.formatting import lines_text_from_dict
from ..utils.tools.time_handlers import ParseDateTime


class NotifierHeaders(BaseModel):
    debug: str = (
        """This is a debbug message. If you see this, debbug=True\n\n"""
    )
    error: str = """An error occur. Details: \n\n"""
    trade: str = """Trade alert! Order details: \n\n"""


class TradingMonitor(BaseModel):
    """A collection of formated commom messages that should be useful
    to monitoring trading routines."""

    start: str = "Starting monitor {}\n\n. Setup:\n{}"
    time: str = "Time now (UTC) = {}\nSleeping {} s."
    stop: str = "Monitor {} finalized!"

    def starting(self, id_: Union[str, int], setup: BaseModel) -> str:
        """The startup message fires when an operation starts.

        Args:
            id_ (Union[str, int]): Operations' Id
            setup (BaseModel): The operational setup

        Returns:
            str: A unique controller message
        """

        monitor_setup = lines_text_from_dict(setup.as_dict())
        return self.start.format(id_, monitor_setup)

    def time_monitoring(self, now: int, step: int) -> str:
        """Human readable formatted message about cycle time.

        Args:
            now (int): timestamp of cycle current datetime
            step (int): seconds to the next 'now'

        Returns:
            str: Periodically time monitoring message
        """

        return self.time.format(
            ParseDateTime(now).to_human_readable(), str(step)
        )

    def stopping(self, id_: Union[str, int]) -> str:
        """If an operation stops, the attribute 'operation.is_running'
        assumes 'False', then this message is send to notifier.

        Args:
            id_ (Union[str, int]): Operations' Id

        Returns:
            str: Final monitoring message
        """

        return self.stop.format(id_)


class Messages(BaseModel):
    notifier_headers: NotifierHeaders = NotifierHeaders()
    trading_monitor: TradingMonitor = TradingMonitor()
