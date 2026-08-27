import os

from dotenv import load_dotenv


load_dotenv()


STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "local")
STORAGE_PATH = os.getenv("STORAGE_PATH", "./evidence-data")
MAX_UPLOAD_SIZE_BYTES = int(os.getenv("MAX_UPLOAD_SIZE_BYTES", 50 * 1024 * 1024))