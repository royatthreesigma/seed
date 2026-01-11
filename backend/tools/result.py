from __future__ import annotations
import json
import traceback
from dataclasses import dataclass
from enum import Enum
from typing import (
    Any,
    Generic,
    Literal,
    Mapping,
    Optional,
    TypeAlias,
    TypeVar,
    overload,
    NoReturn,
)

T = TypeVar("T")


class ErrorCode(str, Enum):
    NOT_FOUND = "NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    EXECUTION_ERROR = "EXECUTION_ERROR"


def _get_pretty_message(
    code: Optional[ErrorCode], custom_message: Optional[str]
) -> str:
    """
    Returns a user-friendly message that can be safely bubbled to clients.
    Sanitizes technical details while preserving meaningful information.
    """
    if custom_message:
        return custom_message

    if code is None:
        return "Operation completed successfully"

    code_messages = {
        ErrorCode.NOT_FOUND: "The requested resource could not be found.",
        ErrorCode.VALIDATION_ERROR: "Validation failed. Please check your input and try again.",
        ErrorCode.EXECUTION_ERROR: "An error occurred while processing your request. Please try again.",
        ErrorCode.PERMISSION_DENIED: "You don't have permission to perform this action.",
    }

    return code_messages.get(code, "An error occurred")


@dataclass(frozen=True, slots=True)
class Result(Generic[T]):
    """Base class for Success and Failure results with common interface."""

    ok: bool
    code: Optional[ErrorCode]
    message: Optional[str]
    value: T | None
    exception: Optional[Exception]
    details: Optional[Mapping[str, Any]]
    pretty_message: Optional[str]

    def is_ok(self) -> bool:
        """Returns True if this is a Success, False if Failure."""
        return self.ok

    def is_err(self) -> bool:
        """Returns True if this is a Failure, False if Success."""
        return not self.ok

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary representation."""
        d: dict[str, Any] = {
            "ok": self.ok,
            "prettyMessage": _get_pretty_message(self.code, self.pretty_message),
        }

        if self.ok:
            d["value"] = self.value
        else:
            d["code"] = (
                self.code.value if self.code else ErrorCode.EXECUTION_ERROR.value
            )
            d["message"] = self.message or "Unknown error"
            if self.exception is not None:
                d["exception"] = str(self.exception)
                d["stack_trace"] = "".join(
                    traceback.format_exception(
                        type(self.exception),
                        self.exception,
                        self.exception.__traceback__,
                    )
                )

        if self.message is not None and self.ok:
            d["message"] = self.message
        if self.code is not None and self.ok:
            d["code"] = self.code.value
        if self.details is not None:
            d["details"] = dict(self.details)

        return d

    def to_json(self) -> str:
        """Convert result to JSON string."""
        return json.dumps(self.to_dict(), default=str)


@dataclass(frozen=True, slots=True)
class Success(Result[T]):
    ok: Literal[True] = True
    code: Optional[ErrorCode] = None
    message: Optional[str] = None
    value: T | None = None
    exception: Optional[Exception] = None
    details: Optional[Mapping[str, Any]] = None
    pretty_message: Optional[str] = None


@dataclass(frozen=True, slots=True)
class Failure(Result[None]):
    ok: Literal[False] = False
    code: ErrorCode = ErrorCode.EXECUTION_ERROR
    message: str = "Unknown error"
    value: None = None
    exception: Optional[Exception] = None
    details: Optional[Mapping[str, Any]] = None
    pretty_message: Optional[str] = None


ResultType: TypeAlias = Success[T] | Failure


@overload
def success() -> Success[None]: ...
@overload
def success(value: T) -> Success[T]: ...
@overload
def success(value: T, *, message: str) -> Success[T]: ...
@overload
def success(value: T, *, pretty_message: str) -> Success[T]: ...
@overload
def success(*, message: str) -> Success[None]: ...
@overload
def success(*, pretty_message: str) -> Success[None]: ...
def success(
    value: T | None = None,
    *,
    message: Optional[str] = None,
    pretty_message: Optional[str] = None,
) -> Success[T]:
    return Success(value=value, message=message, pretty_message=pretty_message)


def failure(
    message: str,
    *,
    code: ErrorCode = ErrorCode.EXECUTION_ERROR,
    details: Optional[Mapping[str, Any]] = None,
    pretty_message: Optional[str] = None,
) -> Failure:
    return Failure(
        code=code,
        message=message,
        details=details,
        pretty_message=pretty_message,
    )


def failure_from_exception(
    exception: Exception,
    *,
    code: ErrorCode = ErrorCode.EXECUTION_ERROR,
    message: Optional[str] = None,
    details: Optional[Mapping[str, Any]] = None,
    pretty_message: Optional[str] = None,
) -> Failure:
    return Failure(
        code=code,
        message=message if message is not None else str(exception),
        exception=exception,
        details=details,
        pretty_message=pretty_message,
    )


class ResultError(Exception):
    def __init__(self, failure: Failure):
        super().__init__(f"{failure.code.value}: {failure.message}")
        self.failure = failure
        self.code = failure.code
        self.message = failure.message
        self.details = failure.details


"""
assert_ok
- If you pass it a Success[T], it extracts the value and returns it.
- If you pass it a Failure, it raises a ResultError (wrapping the failure).

When to use it
Inside lower-level helper functions → probably avoid it, keep working with Result objects 
(so failures can bubble up cleanly).

At a boundary (API controller, background worker entrypoint, CLI command) → use assert_ok to 
unwrap, then rely on your global exception handler to map errors into HTTP responses, logs, etc.
"""


@overload
def assert_ok(res: Success[T]) -> T: ...


@overload
def assert_ok(res: Failure) -> NoReturn: ...


def assert_ok(res: ResultType[T]) -> T:
    if res.ok:
        return res.value  # type: ignore[return-value]
    raise ResultError(res)


# ----- helpers
def compile_errors(results: list[ResultType[Any]]) -> str:
    """Compile pretty messages from all failures in a list of results."""
    errors = [res for res in results if not res.ok]
    combined_message = ""
    for err in errors:
        pretty = _get_pretty_message(err.code, err.pretty_message)
        combined_message += f"{pretty}\n"
    return combined_message.rstrip()
