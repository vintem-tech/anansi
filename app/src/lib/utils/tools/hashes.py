import hashlib
from pydantic import BaseModel


def hash_from_an_object(obj: BaseModel, hash_length: int = 8) -> str:
    return hashlib.sha256(str(obj).encode("utf-8")).hexdigest()[:hash_length]

def another_hash_from_an_object(obj: BaseModel, hash_length: int = 8) -> str:
    return int(hashlib.md5(str(obj).encode("utf-8")).hexdigest(), hash_length)

def string_hash_from_string(input_string:str, hash_len=8):
    _hash = hashlib.md5(input_string.encode("utf-8")).hexdigest()
    return _hash[:hash_len]