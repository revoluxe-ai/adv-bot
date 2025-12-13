#!/bin/sh
set -e

echo "[INIT] Updating pg_hba.conf to allow remote host connections for tests..."
cat <<'EOF' >> "$PGDATA/pg_hba.conf"
host    all             all             0.0.0.0/0               scram-sha-256
host    all             all             ::/0                    scram-sha-256
EOF



