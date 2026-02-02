#!/usr/bin/env python3
"""
discord-intel/scripts/search-lancedb.py
Semantic search over indexed Discord messages.

Usage: python search-lancedb.py <lancedb_path> <query> [--limit N] [--channel X] [--author Y]
"""

import sys
from pathlib import Path

try:
    import lancedb
    from sentence_transformers import SentenceTransformer
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False


def search(db_path: str, query: str, limit: int = 10, channel: str = None, author: str = None):
    """Semantic search over indexed Discord messages"""
    model = SentenceTransformer('all-MiniLM-L6-v2')
    db = lancedb.connect(db_path)
    
    try:
        table = db.open_table('discord_messages')
    except Exception as e:
        print(f"Error: Could not open table 'discord_messages': {e}")
        print("Make sure you've run index-to-lancedb.py first")
        sys.exit(1)
    
    query_vector = model.encode(query).tolist()
    
    # Build query
    search_query = table.search(query_vector)
    
    # Apply filters
    filters = []
    if channel:
        filters.append(f"channel = '{channel}'")
    if author:
        filters.append(f"author = '{author}'")
    
    if filters:
        search_query = search_query.where(" AND ".join(filters))
    
    results = search_query.limit(limit).to_pandas()
    
    if results.empty:
        print("No results found")
        return
    
    print(f"Found {len(results)} results for: '{query}'\n")
    print("-" * 60)
    
    for _, row in results.iterrows():
        content = row['content']
        if len(content) > 200:
            content = content[:200] + "..."
        
        print(f"[#{row['channel']}] @{row['author']}")
        print(f"  {content}")
        print(f"  Distance: {row['_distance']:.4f} | {row.get('timestamp', 'N/A')[:10]}")
        print()


def main():
    if not HAS_DEPS:
        print("Error: Required dependencies not installed")
        print("Install with: pip install lancedb sentence-transformers")
        sys.exit(1)
    
    if len(sys.argv) < 3:
        print("Usage: python search-lancedb.py <lancedb_path> <query> [options]")
        print("\nOptions:")
        print("  --limit N      Number of results (default: 10)")
        print("  --channel X    Filter by channel name")
        print("  --author Y     Filter by author name")
        sys.exit(1)
    
    db_path = sys.argv[1]
    
    # Parse args
    query_parts = []
    limit = 10
    channel = None
    author = None
    
    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == '--limit' and i + 1 < len(args):
            limit = int(args[i + 1])
            i += 2
        elif args[i] == '--channel' and i + 1 < len(args):
            channel = args[i + 1]
            i += 2
        elif args[i] == '--author' and i + 1 < len(args):
            author = args[i + 1]
            i += 2
        else:
            query_parts.append(args[i])
            i += 1
    
    query = ' '.join(query_parts)
    
    if not query:
        print("Error: No query provided")
        sys.exit(1)
    
    if not Path(db_path).exists():
        print(f"Error: {db_path} does not exist")
        sys.exit(1)
    
    search(db_path, query, limit, channel, author)


if __name__ == "__main__":
    main()
