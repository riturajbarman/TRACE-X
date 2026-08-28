import os

from dotenv import load_dotenv


load_dotenv()


STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "local")
STORAGE_PATH = os.getenv("STORAGE_PATH", "./evidence-data")
MAX_UPLOAD_SIZE_BYTES = int(os.getenv("MAX_UPLOAD_SIZE_BYTES", 50 * 1024 * 1024))

# Allowed browser origins for CORS — comma-separated list.
# Default covers the local Next.js dev server.
# Override in production via environment variable, never use "*" in production.
_cors_raw = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
CORS_ALLOWED_ORIGINS: list[str] = [o.strip() for o in _cors_raw.split(",") if o.strip()]