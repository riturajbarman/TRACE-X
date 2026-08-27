import os

from dotenv import load_dotenv


load_dotenv()


STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "local")
STORAGE_PATH = os.getenv("STORAGE_PATH", "./evidence-data")