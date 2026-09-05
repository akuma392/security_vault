from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"
DB_PATH = BASE_DIR / "vault.db"

# Ensure storage directory exists
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# Default expiry in seconds (e.g., 24 hours)
DEFAULT_EXPIRY_SECONDS = 86400
# Janitor cleanup check interval in seconds
CLEANUP_INTERVAL_SECONDS = 60