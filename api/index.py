"""Vercel serverless entry point for the AI Mock Interview Bot API."""
from __future__ import annotations

import sys
import os
from pathlib import Path

# Add backend directory to Python path so `from app.xxx` imports work
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# On Vercel the filesystem is read-only except /tmp.
# Override data_dir before any app module is imported.
if not os.environ.get("DATA_DIR"):
    os.environ["DATA_DIR"] = "/tmp/moc_data"

from app.main import app  # noqa: E402  (must come after sys.path fix)

# Vercel looks for a variable named `app` (ASGI/WSGI callable)
__all__ = ["app"]
