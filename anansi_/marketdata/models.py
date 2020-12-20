# pylint: disable=no-name-in-module
# pylint: disable=no-self-argument

""" Classes que abstraem dados que transitam entre partes diferentes do
sistema.
"""

from pydantic import BaseModel
#from typing import Sequence

class Market(BaseModel):
    """ Market attributes """

    broker_name: str
    ticker_symbol: str