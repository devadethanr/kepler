def main() -> None:
    """Start the worker without importing it while resolving the package."""
    from .worker import main as worker_main

    worker_main()

__all__ = ["main"]
