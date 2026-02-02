#!/usr/bin/env python3
"""
discord-intel/scripts/index-to-lancedb.py
Index SAFE Discord messages from SQLite into LanceDB.

Usage: python index-to-lancedb.py <sqlite_db> <lancedb_path>

Only indexes messages with safety_status = 'safe'.
"""

import sqlite3
import sys
from pathlib import Path

try:
    import lancedb
    from sentence_transformers import SentenceTransformer
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False


def index_safe_messages(db_path: str, lance_path: str):
    """Index only safe messages from SQLite into LanceDB"""
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # Connect to SQLite
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # Get ONLY safe messages
    cursor = conn.execute("""
        SELECT id, channel_name, author_name, content, timestamp
        FROM messages 
        WHERE safety_status = 'safe' 
          AND content IS NOT NULL 
          AND LENGTH(content) >= 10
    """)
    
    records = []
    for row in cursor:
        content = row['content']
        records.append({
            'id': row['id'],
            'channel': row['channel_name'],
            'author': row['author_name'],
            'content': content,
            'timestamp': row['timestamp'] or '',
            'vector': model.encode(content).tolist()
        })
    
    conn.close()
    
    if not records:
        print("No safe messages to index")
        return
    
    # Index to LanceDB
    db = lancedb.connect(lance_path)
    table = db.create_table('discord_messages', records, mode='overwrite')
    
    print(f"✅ Indexed {len(records)} SAFE messages → {lance_path}")


def main():
    if not HAS_DEPS:
        print("Error: Required dependencies not installed")
        print("Install with: pip install lancedb sentence-transformers")
        sys.exit(1)
    
    if len(sys.argv) < 3:
        print("Usage: python index-to-lancedb.py <sqlite_db> <lancedb_path>")
        print("\nOnly indexes messages marked as 'safe' by safety evaluator.")
        sys.exit(1)
    
    db_path = sys.argv[1]
    lance_path = sys.argv[2]
    
    if not Path(db_path).exists():
        print(f"Error: {db_path} does not exist")
        sys.exit(1)
    
    index_safe_messages(db_path, lance_path)


if __name__ == "__main__":
    main()
