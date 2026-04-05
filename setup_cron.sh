#!/bin/bash
# setup_cron.sh — Install cron job to run flight scraper every 4 hours

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$(which python3)"
MAIN="${SCRIPT_DIR}/src/main.py"
LOG_DIR="${SCRIPT_DIR}/logs"

mkdir -p "$LOG_DIR"

CRON_CMD="0 */4 * * * cd ${SCRIPT_DIR} && ${PYTHON} ${MAIN} >> ${LOG_DIR}/cron.log 2>&1"

# Check if cron job already exists
(crontab -l 2>/dev/null | grep -F "$MAIN") && {
    echo "Cron job already exists. Skipping."
    exit 0
}

# Add to crontab
(crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -

echo "Cron job installed: every 4 hours"
echo "   $CRON_CMD"
echo ""
echo "To verify: crontab -l"
echo "To remove: crontab -e (and delete the line)"
