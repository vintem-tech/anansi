import hashlib
from pydantic import BaseModel


def hash_from_an_object(obj: BaseModel, hash_length: int = 8) -> str:
    return hashlib.sha256(str(obj).encode("utf-8")).hexdigest()[:hash_length]
