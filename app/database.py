import sqlite3
import time
from app.config import DB_PATH

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS vault_files (
                id TEXT PRIMARY KEY,
                original_filename TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                storage_filename TEXT NOT NULL,
                max_downloads INTEGER DEFAULT 1,
                download_count INTEGER DEFAULT 0,
                view_mode TEXT DEFAULT 'download',
                view_duration INTEGER DEFAULT 10,
                expires_at REAL NOT NULL,
                created_at REAL NOT NULL
            )
        """)
        conn.commit()

def save_file_record(file_id: str, original_name: str, size: int, storage_name: str, 
                     max_downloads: int, expires_in: int, view_mode: str = "download", view_duration: int = 10):
    now = time.time()
    expires_at = now + expires_in
    with get_db() as conn:
        conn.execute("""
            INSERT INTO vault_files 
            (id, original_filename, file_size, storage_filename, max_downloads, download_count, view_mode, view_duration, expires_at, created_at)
            VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?, ?)
        """, (file_id, original_name, size, storage_name, max_downloads, view_mode, view_duration, expires_at, now))
        conn.commit()

def get_file_record(file_id: str):
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM vault_files WHERE id = ?", (file_id,))
        return cursor.fetchone()

def increment_download(file_id: str):
    with get_db() as conn:
        conn.execute("UPDATE vault_files SET download_count = download_count + 1 WHERE id = ?", (file_id,))
        conn.commit()

def delete_file_record(file_id: str):
    with get_db() as conn:
        conn.execute("DELETE FROM vault_files WHERE id = ?", (file_id,))
        conn.commit()

def get_expired_or_exhausted_records():
    now = time.time()
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT * FROM vault_files 
            WHERE expires_at <= ? OR download_count >= max_downloads
        """, (now,))
        return cursor.fetchall()