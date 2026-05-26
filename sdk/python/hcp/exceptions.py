from __future__ import annotations


class HCPError(Exception):
    """Base exception for HCP SDK errors."""

    def __init__(self, message: str, status_code: int | None = None, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


class AuthenticationError(HCPError):
    pass


class PermissionError(HCPError):
    pass


class NotFoundError(HCPError):
    pass


class ValidationError(HCPError):
    pass


class RateLimitError(HCPError):
    pass


class ServerError(HCPError):
    pass


class ParseTimeoutError(HCPError):
    pass


def raise_for_status(response: object) -> None:
    import httpx

    if not isinstance(response, httpx.Response):
        return
    if response.status_code < 400:
        return

    body: dict = {}
    try:
        data = response.json()
        if isinstance(data, dict) and "error" in data:
            err = data["error"]
            if isinstance(err, dict):
                body = err
    except Exception:
        pass

    message = str(body.get("message", response.text or response.reason_phrase))
    code = body.get("code")
    status = response.status_code

    mapping: dict[int, type[HCPError]] = {
        401: AuthenticationError,
        403: PermissionError,
        404: NotFoundError,
        422: ValidationError,
        429: RateLimitError,
    }
    if status >= 500:
        raise ServerError(message, status, code)
    exc_cls = mapping.get(status, HCPError)
    raise exc_cls(message, status, code)
