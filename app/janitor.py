import asyncio
import os
from app.config import STORAGE_DIR, CLEANUP_INTERVAL_SECONDS
from app.database import get_expired_or_exhausted_records, delete_file_record

async def cleanup_loop():
    while True:
        try:
            records = get_expired_or_exhausted_records()
            for record in records:
                storage_path = STORAGE_DIR / record["storage_filename"]
                if storage_path.exists():
                    try:
                        os.remove(storage_path)
                    except OSError:
                        pass
                delete_file_record(record["id"])
        except Exception as e:
            print(f"[Janitor Error] {e}")

        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)