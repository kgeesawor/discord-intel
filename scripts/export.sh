#!/bin/bash
# discord-intel/scripts/export.sh
# Generic Discord channel exporter
# Usage: ./export.sh [config_file] [days_back]

set -e

CONFIG_FILE="${1:-./discord-channels.conf}"
DAYS_BACK="${2:-1}"

# Token
TOKEN_FILE="${DISCORD_TOKEN_FILE:-$HOME/.config/discord-exporter-token}"
if [ ! -f "$TOKEN_FILE" ]; then
    echo "ERROR: Token not found at $TOKEN_FILE"
    echo "See SKILL.md for token setup instructions"
    exit 1
fi
TOKEN=$(cat "$TOKEN_FILE")

# Exporter path (adjust for your system)
DCE="${DISCORD_EXPORTER:-DiscordChatExporter.Cli}"
if ! command -v "$DCE" &> /dev/null; then
    echo "ERROR: DiscordChatExporter.Cli not found"
    echo "Install from: https://github.com/Tyrrrz/DiscordChatExporter"
    echo "Or set DISCORD_EXPORTER=/path/to/DiscordChatExporter.Cli"
    exit 1
fi

# Output
OUTPUT_DIR="${DISCORD_OUTPUT_DIR:-./discord-export/$(date +%Y-%m-%d)}"
mkdir -p "$OUTPUT_DIR"

# Date calculation (macOS vs Linux)
if date -v-1d &> /dev/null; then
    AFTER_DATE=$(date -v-${DAYS_BACK}d +%Y-%m-%d)
else
    AFTER_DATE=$(date -d "-${DAYS_BACK} days" +%Y-%m-%d)
fi

echo "Discord Export"
echo "=============="
echo "Config: $CONFIG_FILE"
echo "Lookback: $DAYS_BACK days (after $AFTER_DATE)"
echo "Output: $OUTPUT_DIR"
echo ""

# Config file format (one per line):
# CHANNEL_ID:channel_name
# Or for entire guild:
# GUILD:SERVER_ID

if [ ! -f "$CONFIG_FILE" ]; then
    echo "No config file found. Creating template at $CONFIG_FILE"
    cat > "$CONFIG_FILE" << 'EOF'
# Discord Export Configuration
# Format: CHANNEL_ID:name (for single channel)
# Format: GUILD:SERVER_ID (for entire server)
#
# Example:
# 1234567890:general
# 1234567891:announcements
# GUILD:9876543210
EOF
    echo "Edit $CONFIG_FILE and re-run"
    exit 0
fi

# Export each channel/guild
while IFS=: read -r TYPE_OR_ID NAME_OR_ID || [ -n "$TYPE_OR_ID" ]; do
    # Skip comments and empty lines
    [[ "$TYPE_OR_ID" =~ ^#.*$ ]] && continue
    [[ -z "$TYPE_OR_ID" ]] && continue
    
    if [ "$TYPE_OR_ID" = "GUILD" ]; then
        echo "Exporting entire guild $NAME_OR_ID..."
        "$DCE" exportguild \
            --token "$TOKEN" \
            --guild "$NAME_OR_ID" \
            --format "Json" \
            --output "$OUTPUT_DIR" \
            --after "$AFTER_DATE" \
            --media false \
            2>&1 || echo "  Warning: Guild export may have failed"
    else
        CHANNEL_ID="$TYPE_OR_ID"
        CHANNEL_NAME="${NAME_OR_ID:-$CHANNEL_ID}"
        OUTPUT_FILE="$OUTPUT_DIR/${CHANNEL_NAME}.json"
        
        echo "Exporting #$CHANNEL_NAME ($CHANNEL_ID)..."
        "$DCE" export \
            --token "$TOKEN" \
            --channel "$CHANNEL_ID" \
            --format "Json" \
            --output "$OUTPUT_FILE" \
            --after "$AFTER_DATE" \
            --media false \
            2>&1 || echo "  Warning: Export failed for $CHANNEL_NAME"
    fi
done < "$CONFIG_FILE"

echo ""
echo "Export complete: $OUTPUT_DIR"
echo "Files: $(ls -1 "$OUTPUT_DIR"/*.json 2>/dev/null | wc -l | tr -d ' ') JSON files"
