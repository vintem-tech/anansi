# pylint:disable=missing-module-docstring
# pylint:disable=missing-class-docstring
# pylint:disable=missing-function-docstring

import json
from collections import namedtuple


class Serialize:
    def __init__(self, target: object):
        self.target = target

    def to_dict(self) -> dict:
        return json.loads(
            json.dumps(self.target, default=lambda o: o.__dict__, indent=0)
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class Deserialize:
    def __init__(self, name="X"):
        self.name = name

    def _json_object_hook(self, dict_):
        return namedtuple(self.name, dict_.keys())(*dict_.values())

    def from_json(self, json_in: str) -> object:
        return json.loads(json_in, object_hook=self._json_object_hook)

    def from_dict(self, dict_in: dict) -> object:
        return self.from_json(json_in=json.dumps(dict_in))
