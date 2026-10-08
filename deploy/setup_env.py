"""Generate local credentials without printing them or replacing an existing file."""
import secrets
from pathlib import Path

target = Path(__file__).resolve().parents[1] / ".env"
try:
    with target.open("x", encoding="utf-8") as stream:
        for key in ("POSTGRES_PASSWORD", "APP_DB_PASSWORD", "DEMO_PASSWORD"):
            stream.write(f"{key}={secrets.token_hex(24)}\n")
        stream.write("API_PORT=8020\n")
except FileExistsError:
    print("Existing .env preserved")
else:
    print("Created ignored .env with random local credentials")
