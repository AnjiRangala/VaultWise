from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import Request, Response

from app.request_context import request_id_context


async def request_id_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    request_id = request.headers.get("X-Request-ID") or request_id_context.get()
    if not request_id:
        request_id = str(uuid4())
    request_id_context.set(request_id)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response
