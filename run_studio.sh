#!/usr/bin/env bash
set -euo pipefail

# 1 activate the venv
source venv/bin/activate

# 2 start or create Postgres
docker start langgraph-db 2>/dev/null || \
docker run -d --name langgraph-db -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:16

export LG_DB_URI="postgresql://postgres:postgres@localhost:5432/postgres"

# 3 create checkpoint tables (idempotent)
python - <<'PY'
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg import connect, OperationalError
import os, time

uri = os.environ["LG_DB_URI"]
for _ in range(15):
    try:
        connect(uri).close(); break
    except OperationalError:
        time.sleep(1)

with PostgresSaver.from_conn_string(uri) as saver:
    saver.setup()
PY

# 4 run the dev server + Studio UI
langgraph dev --port 2024
