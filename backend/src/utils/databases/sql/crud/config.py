# pylint:disable=bare-except
# pylint:disable=missing-module-docstring

import json
from typing import Union

from pony.orm import db_session

from .....config import messages, preferences
from ..models.config import Messages, Preferences


@db_session
def create_messages(messages_: messages.Messages):
    Messages(
        **dict(
            notifier_headers=messages_.notifier_headers.json(),
            trading_monitor=messages_.trading_monitor.json(),
        )
    )


@db_session
def create_preferences(preferences_: preferences.Preferences):
    Preferences(
        **dict(
            date_time=preferences_.date_time.json(),
            back_testing=preferences_.back_testing.json(),
            notifier=preferences_.notifier.json(),
            trading=preferences_.trading.json(),
        )
    )


@db_session
def read_messages() -> Union[None, messages.Messages]:
    try:
        messages_ = Messages.get()

        return messages.Messages(
            notifier_headers=messages.NotifierHeaders(
                **(json.loads(messages_.notifier_headers))
            ),
            trading_monitor=messages.TradingMonitor(
                **(json.loads(messages_.trading_monitor))
            ),
        )

    except:
        return None


@db_session
def read_preferences() -> Union[None, preferences.Preferences]:
    try:
        preferences_ = Preferences.get()

        return preferences.Preferences(
            date_time=preferences.DateTimesettings(
                **(json.loads(preferences_.date_time))
            ),
            back_testing=preferences.BackTesting(
                **(json.loads(preferences_.back_testing))
            ),
            notifier=preferences.Notifier(
                **(json.loads(preferences_.notifier))
            ),
            trading=preferences.Trading(**(json.loads(preferences_.trading))),
        )

    except:
        return None
