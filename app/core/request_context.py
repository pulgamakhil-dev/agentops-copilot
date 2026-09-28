from uuid import uuid4

from fastapi import Request

from app.core.logging import (
    clear_request_id,
    set_request_id,
)


async def request_context_middleware(
    request: Request,
    call_next,
):
    """
    Attach a request ID to every incoming HTTP request.

    If the client provides X-Request-ID, reuse it.
    Otherwise generate a new UUID.
    """

    request_id = (
        request.headers.get("X-Request-ID")
        or str(uuid4())
    )

    set_request_id(request_id)

    try:
        response = await call_next(request)

        # Return the request ID to the caller for traceability.
        response.headers["X-Request-ID"] = request_id

        return response

    finally:
        clear_request_id()