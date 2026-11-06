from contextvars import ContextVar
from uuid import uuid4

request_id_context: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    request_id = request_id_context.get()
    return request_id or str(uuid4())
