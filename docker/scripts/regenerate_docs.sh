#!/bin/bash
# Regenerate EntitySpine documentation from source annotations

set -e

TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
LOG_FILE="/var/log/docs-regen.log"

echo "[$TIMESTAMP] ========================================" >> "$LOG_FILE"
echo "[$TIMESTAMP] Starting docs regeneration..." >> "$LOG_FILE"

cd /app

# Check if doc_automation is available
if [ -d "/app/doc_automation" ] && [ -f "/app/doc_automation/__init__.py" ]; then
    echo "[$TIMESTAMP] Running docbuilder..." >> "$LOG_FILE"
    
    python -c "
import sys
from pathlib import Path
sys.path.insert(0, '/app')
try:
    from doc_automation.orchestrator import DocumentationOrchestrator
    orchestrator = DocumentationOrchestrator(
        project_root=Path('/app/src'),
        output_dir=Path('/app/docs/generated')
    )
    orchestrator.generate_all()
    print('Documentation generated')
except Exception as e:
    import traceback
    print(f'Docbuilder error: {e}')
    traceback.print_exc()
" 2>> "$LOG_FILE" || echo "[$TIMESTAMP] docbuilder completed with warnings" >> "$LOG_FILE"
else
    echo "[$TIMESTAMP] doc_automation not found, skipping annotation extraction" >> "$LOG_FILE"
fi

# Build mkdocs site
if [ -f "/app/mkdocs.yml" ]; then
    echo "[$TIMESTAMP] Building MkDocs..." >> "$LOG_FILE"
    mkdocs build --site-dir /app/site 2>> "$LOG_FILE" || echo "[$TIMESTAMP] MkDocs warning" >> "$LOG_FILE"
    echo "[$TIMESTAMP] Build complete" >> "$LOG_FILE"
else
    echo "[$TIMESTAMP] No mkdocs.yml found" >> "$LOG_FILE"
fi

echo "[$TIMESTAMP] Done" >> "$LOG_FILE"
