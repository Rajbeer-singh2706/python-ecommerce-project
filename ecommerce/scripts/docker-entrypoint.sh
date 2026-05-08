#!/bin/bash
set -e

echo "  🐳  ShopCLI Docker Container"
echo "  ─────────────────────────────"

# Init DB + seed if fresh
if [ ! -f /app/data/ecommerce.db ]; then
    echo "  🌱  First run — initialising database…"
    python main.py reset
    python main.py seed
fi

# Run the interactive CLI
exec python main.py run
