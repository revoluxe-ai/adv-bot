#!/bin/sh
set -e

echo "[INIT] Updating pg_hba.conf to allow remote host connections for tests..."
cat <<'EOF' >> "$PGDATA/pg_hba.conf"
# Allow connections from Docker bridge network (172.18.0.0/16) without encryption for tests
host    all             all             172.18.0.0/16           trust
# Allow connections from localhost without encryption for tests
host    all             all             127.0.0.1/32             trust
host    all             all             ::1/128                  trust
# Allow other connections with scram-sha-256
host    all             all             0.0.0.0/0               scram-sha-256
host    all             all             ::/0                    scram-sha-256
EOF



