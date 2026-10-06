from backend.app import create_app

try:
    app = create_app()
except (ValueError, RuntimeError):
    raise RuntimeError("Backend configuration/model validation failed. Check .env and the pinned model environment; secret values are hidden.") from None
