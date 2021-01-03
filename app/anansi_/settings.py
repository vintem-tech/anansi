# pylint: disable=W0614
# pylint: disable= W0401
# pylint: disable=no-name-in-module
# pylint: disable=no-self-argument
# pylint: disable=too-few-public-methods
"""General settings centralized here """
import sys
from .brokers.settings import *


thismodule = sys.modules[__name__]
klines_desired_informations = BrokerSettings().kline_information


def get_settings():
    """Deve procurar as configurações no banco de dados, caso não existam, criar
    as configurações-padrão a partir dos valores declarados nos módulos
    'settings' de cada pacote. Por hora, retorna as configurações-padrão, sem
    consulta/escrita ao banco de dados.

    Returns:
        [type]: [description]
    """
    # return DefaultSettings()
    return thismodule
