#!/usr/bin/env python3
"""
discord-intel/scripts/to-sqlite.py
Convert Discord JSON exports to SQLite for safe querying.

Usage: python to-sqlite.py <json_dir> <sqlite_db>

The SQLite database provides a security buffer - agents can query
without direct exposure to potentially malicious message content.
"""

import json
import sqlite3
import sys
from pathlib import Path
from datetime import datetime


def init_db(db_path: str) -> sqlite3.Connection:
    """Initialize SQLite database with schema"""
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            channel_id TEXT,
            channel_name TEXT,
            author_id TEXT,
            author_name TEXT,
            content TEXT,
            timestamp TEXT,
            timestamp_epoch INTEGER,
            reply_to TEXT,
            attachments_count INTEGER,
            reactions_count INTEGER,
            is_pinned INTEGER,
            export_date TEXT,
            safety_status TEXT DEFAULT 'pending',
            safety_score REAL,
            safety_flags TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_author ON messages(author_name)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_channel ON messages(channel_name)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON messages(timestamp_epoch)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_content_fts ON messages(content)")
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            id TEXT PRIMARY KEY,
            name TEXT,
            category TEXT,
            topic TEXT,
            message_count INTEGER,
            last_export TEXT
        )
    """)
    conn.commit()
    return conn


def parse_timestamp(ts: str) -> tuple:
    """Parse Discord timestamp to string and epoch"""
    formats = [
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z", 
        "%Y-%m-%dT%H:%M:%S"
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(ts.replace("+00:00", "+0000"), fmt)
            return ts, int(dt.timestamp())
        except ValueError:
            continue
    return ts, 0


def load_json_file(json_path: Path, conn: sqlite3.Connection, export_date: str) -> int:
    """Load a single JSON export file into SQLite"""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"  Error reading {json_path}: {e}")
        return 0
    
    channel = data.get('channel', {})
    channel_id = channel.get('id', '')
    channel_name = channel.get('name', json_path.stem)
    category = channel.get('category', '')
    topic = channel.get('topic', '')
    
    messages = data.get('messages', [])
    inserted = 0
    
    for msg in messages:
        msg_id = msg.get('id', '')
        author = msg.get('author', {})
        content = msg.get('content', '')
        timestamp = msg.get('timestamp', '')
        ts_str, ts_epoch = parse_timestamp(timestamp)
        
        reply_to = msg.get('reference', {}).get('messageId') if msg.get('reference') else None
        attachments_count = len(msg.get('attachments', []))
        reactions_count = sum(r.get('count', 0) for r in msg.get('reactions', []))
        is_pinned = 1 if msg.get('isPinned') else 0
        
        try:
            conn.execute("""
                INSERT OR REPLACE INTO messages 
                (id, channel_id, channel_name, author_id, author_name, content, 
                 timestamp, timestamp_epoch, reply_to, attachments_count, 
                 reactions_count, is_pinned, export_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                msg_id, channel_id, channel_name,
                author.get('id', ''), author.get('name', ''),
                content, ts_str, ts_epoch, reply_to,
                attachments_count, reactions_count, is_pinned, export_date
            ))
            inserted += 1
        except Exception as e:
            print(f"  Error inserting message {msg_id}: {e}")
    
    conn.execute("""
        INSERT OR REPLACE INTO channels (id, name, category, topic, message_count, last_export)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (channel_id, channel_name, category, topic, len(messages), export_date))
    
    conn.commit()
    return inserted


def main():
    if len(sys.argv) < 3:
        print("Usage: python to-sqlite.py <json_dir> <sqlite_db>")
        print("\nConverts Discord JSON exports to SQLite for safe querying.")
        sys.exit(1)
    
    json_dir = Path(sys.argv[1])
    db_path = sys.argv[2]
    export_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if not json_dir.exists():
        print(f"Error: Directory {json_dir} does not exist")
        sys.exit(1)
    
    print(f"Initializing database: {db_path}")
    conn = init_db(db_path)
    
    json_files = list(json_dir.glob("*.json"))
    print(f"Found {len(json_files)} JSON files")
    
    total_messages = 0
    for json_file in sorted(json_files):
        print(f"  Loading {json_file.name}...", end=" ")
        count = load_json_file(json_file, conn, export_date)
        total_messages += count
        print(f"({count} messages)")
    
    conn.close()
    print(f"\nTotal: {total_messages} messages → {db_path}")


if __name__ == "__main__":
    main()
