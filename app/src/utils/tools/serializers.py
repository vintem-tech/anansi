import json
from collections import namedtuple

class Serialize:
    def __init__(self, Target: object):
        self.Target = Target

    def to_dict(self) -> dict:
        return json.loads(
            json.dumps(self.Target, default=lambda o: o.__dict__, indent=0)
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class Deserialize:
    def __init__(self, name="X"):
        self.name = name

    def _json_object_hook(self, d):
        return namedtuple(self.name, d.keys())(*d.values())

    def from_json(self, json_in: str) -> object:
        return json.loads(json_in, object_hook=self._json_object_hook)

    def from_dict(self, dict_in: dict) -> object:
        return self.from_json(json_in=json.dumps(dict_in))