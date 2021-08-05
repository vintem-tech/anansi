# pylint: disable=no-name-in-module
# pylint: disable=E1136
"""An abstraction for outgoing messages"""
from typing import Union  # , Sequence, Optional, List

from pydantic import BaseModel  # , validator

from ..utils.tools.formatting import text_in_lines_from_dict
from ..utils.tools.time_handlers import ParseDateTime


class NotifierHeader:
    debug = """This is a debbug message. If you see this, debbug=True\n\n"""
    error = """An error occur. Details: \n\n"""
    trade = """Trade alert! Order details: \n\n"""

class TradingMonitor:
    """A collection of formated commom messages that should be useful
    to monitoring trading routines."""

    @staticmethod
    def initial(the_id: Union[str, int], setup: BaseModel) -> str:
        """The startup message fires when an operation starts.

        Args:
            the_id (Union[str, int]): Operations' Id
            setup (BaseModel): The operational setup

        Returns:
            str: A unique controller message
        """
        return "Starting Anansi. Your operation id is {}\n\n{}".format(
            the_id, text_in_lines_from_dict(setup.as_dict())
        )

    @staticmethod
    def time_monitoring(now: int, step: int) -> str:
        """Human readable formatted message about cycle time.

        Args:
            now (int): timestamp of cycle current datetime
            step (int): seconds to the next 'now'

        Returns:
            str: Periodically time monitoring message
        """
        return "Time now (UTC) = {}\nSleeping {} s.".format(
            ParseDateTime(now).to_human_readable(), str(step)
        )

    @staticmethod
    def final(the_id: Union[str, int]) -> str:
        """If an operation stops, the attribute 'operation.is_running'
        assumes 'False', then this message is send to notifier.

        Args:
            the_id (Union[str, int]): Operations' Id

        Returns:
            str: Final monitoring message
        """
        return "Op. {} finalized!".format(the_id)
