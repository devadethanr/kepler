from __future__ import annotations

from typing import Any, Dict, Literal
from datetime import datetime

# Global status registry (Lazy evaluation)
# Services are "Healthy" until an operation fails.
_HEALTH_STATUS: Dict[str, Dict[str, Any]] = {
    "nvidia_nim": {"status": "healthy", "last_update": datetime.now(), "error": None},
    "google_gemini": {"status": "healthy", "last_update": datetime.now(), "error": None},
    "news_search": {"status": "healthy", "last_update": datetime.now(), "error": None},
    "kite_api": {"status": "healthy", "last_update": datetime.now(), "error": None},
}

def update_service_status(
    service: Literal["nvidia_nim", "google_gemini", "news_search", "kite_api"],
    is_success: bool,
    error_msg: str | None = None
):
    """Updates the status of a service based on its last operation."""
    if service not in _HEALTH_STATUS:
        return
        
    _HEALTH_STATUS[service]["status"] = "healthy" if is_success else "unhealthy"
    _HEALTH_STATUS[service]["last_update"] = datetime.now()
    _HEALTH_STATUS[service]["error"] = error_msg if not is_success else None

def get_all_statuses() -> Dict[str, str]:
    """Returns a simple map of service statuses for the dashboard."""
    return {svc: info["status"] for svc, info in _HEALTH_STATUS.items()}

def get_service_details(service: str) -> Dict[str, Any] | None:
    """Returns full details for a specific service."""
    return _HEALTH_STATUS.get(service)
