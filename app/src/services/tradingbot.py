from typing import List, Union

from ..lib.utils.databases.sql.models import BackTestingOperation
from ..lib.trading.main import Trader


class BackTesting:
    operations = dict()
    traders = list()

    def get_operations(self) -> List[str]:
        operations_ = BackTestingOperation.select()
        if operations_:
            self.operations = {
                operation.name: operation for operation in operations_
            }

        return self.operations

    def get_a_trader(self, operation_name: str) -> Union[Trader, None]:
        if operation_name in list(self.operations.keys()):
            try:
                return Trader(operation=self.operations.get(operation_name))

            except BaseException as error:
                raise Exception(error) from BaseException

        raise KeyError("{} not found".format(operation_name))
