#!/bin/bash
# Entrypoint for EntitySpine Live Documentation Container

set -e

echo "==========================================="
echo "EntitySpine Live Documentation Container"
echo "==========================================="
echo ""
echo "Configuration:"
echo "  - Source: /app/src (mounted)"
echo "  - Docs:   /app/docs (mounted)"
echo "  - Output: /app/site"
echo "  - Regen:  Every 15 minutes (or REGEN_INTERVAL)"
echo ""

# Update cron interval if REGEN_INTERVAL is set
if [ -n "$REGEN_INTERVAL" ]; then
    echo "*/$REGEN_INTERVAL * * * * /app/regenerate_docs.sh" > /etc/cron.d/docs-regen
    crontab /etc/cron.d/docs-regen
    echo "Cron interval set to $REGEN_INTERVAL minutes"
fi

# Run initial documentation build
echo "Running initial documentation build..."
/app/regenerate_docs.sh || true

# Ensure site directory has content
if [ ! -f "/app/site/index.html" ]; then
    echo "Creating placeholder..."
    mkdir -p /app/site
    cat > /app/site/index.html << 'HTML'
<!DOCTYPE html>
<html>
<head><title>EntitySpine Docs - Building</title></head>
<body style="font-family: sans-serif; padding: 40px;">
<h1>EntitySpine Documentation</h1>
<p>Documentation is being built. Please refresh in a moment.</p>
</body>
</html>
HTML
fi

echo ""
echo "Starting supervisor (cron + http server)..."
echo "Docs available at http://localhost:80"
echo ""

exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
