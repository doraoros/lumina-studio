from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SOURCES = DATA / "sources"
SHOOT = DATA / "shoot"
MODELS = DATA / "models"
UPLOADS = DATA / "uploads"
DB_PATH = DATA / "lumina.db"

DEMO_TARGET = 3000
ALBUM_LIMIT = 160
USER_AGENT = "LuminaStudioDemo/1.0 (educational photo-studio demo)"
