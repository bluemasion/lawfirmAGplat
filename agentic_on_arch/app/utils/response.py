"""Unified JSON response format."""

from typing import Any, Optional


def ok(data: Any = None, message: str = "success") -> dict:
    return {"success": True, "message": message, "data": data}


def fail(message: str = "error", detail: Optional[str] = None) -> dict:
    return {"success": False, "message": message, "detail": detail}
