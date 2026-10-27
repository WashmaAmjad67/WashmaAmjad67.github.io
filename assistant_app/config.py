import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
DATA_DIR = Path(os.getenv("ASSISTANT_DATA_DIR", "data"))
MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
STT_MODEL = os.getenv("OPENAI_STT_MODEL", "gpt-4o-mini-transcribe")
IMAGE_MODEL = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1")
