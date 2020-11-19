# pylint: disable=no-name-in-module
# pylint: disable=no-self-argument

# from typing import Optional

""" Classes que abstraem dados que transitam entre partes diferentes do
sistema.
"""

from pydantic import BaseModel


class Market(BaseModel):
    """ Market attributes """

    broker_name: str
    ticker_symbol: str
    time_frame: str
