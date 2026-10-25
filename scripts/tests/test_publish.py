# -*- coding: utf-8 -*-
"""publish_supabase against a fake Supabase (local HTTP server): paths, headers, batching,
retry behaviour, and that failures are not swallowed."""
import json
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import publish_supabase as ps  # noqa: E402


class Fake(BaseHTTPRequestHandler):
    log: list = []
    fail_first: dict = {}

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        key = self.path.split("?")[0]
        Fake.log.append({"path": self.path, "headers": {k.lower(): v for k, v in self.headers.items()}, "body": body})
        n = Fake.fail_first.get(key, 0)
        if n:
            Fake.fail_first[key] = n - 1
            self.send_response(503)
            self.end_headers()
            return
        if "forbidden" in self.path:
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b'{"message":"nope"}')
            return
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"{}")

    def log_message(self, *a):
        pass


@pytest.fixture()
def server():
    Fake.log, Fake.fail_first = [], {}
    srv = HTTPServer(("127.0.0.1", 0), Fake)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


def client(url):
    return ps.Client(url, "service-key", retries=3, sleep=lambda s: None)


def test_every_polygon_becomes_one_village_row():
    rows = ps.village_rows()
    assert len(rows) == 954
    assert len({r["polygon_id"] for r in rows}) == 954
    assert all(r["tehsil"] and r["village"] for r in rows)


def test_monthly_rows_cover_every_village_and_respect_period_filter():
    one = ps.monthly_rows(["2026-08"])
    assert len(one) == 954 and {r["period"] for r in one} == {"2026-08"}
    assert all(r["cdi_class"] in {"None", "D0", "D1", "D2", "D3", "D4", "ND"} for r in one)
    assert all(r["cdi"] is None or 0 <= r["cdi"] <= 1 for r in one)


def test_upload_uses_upsert_and_service_key(server):
    client(server).upload("latest_status.json", b"{}", "application/json")
    req = Fake.log[0]
    assert req["path"] == f"/storage/v1/object/{ps.BUCKET}/latest_status.json"
    assert req["headers"]["x-upsert"] == "true"
    assert req["headers"]["authorization"] == "Bearer service-key"


def test_upsert_batches_and_names_conflict_columns(server):
    rows = [{"village_id": i, "period": "2026-01"} for i in range(2500)]
    client(server).upsert("village_monthly", rows, "village_id,period")
    assert len(Fake.log) == 3
    assert all("on_conflict=village_id,period" in r["path"] for r in Fake.log)
    assert sum(len(json.loads(r["body"])) for r in Fake.log) == 2500
    assert "merge-duplicates" in Fake.log[0]["headers"]["prefer"]


def test_retries_server_errors_but_not_client_errors(server):
    Fake.fail_first = {"/rest/v1/pipeline_runs": 2}
    client(server).insert("pipeline_runs", {"ok": True})
    assert len(Fake.log) == 3                       # 2 failures then success
    with pytest.raises(ps.PublishError, match="403"):
        client(server).insert("forbidden", {"ok": True})
    assert sum("forbidden" in r["path"] for r in Fake.log) == 1   # 403 is not retried


def test_persistent_failure_raises(server):
    Fake.fail_first = {"/rest/v1/villages": 99}
    with pytest.raises(ps.PublishError):
        client(server).upsert("villages", [{"polygon_id": 1}], "polygon_id")


def test_missing_credentials_raise(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    with pytest.raises(ps.PublishError):
        ps.client_from_env()


# ---- SQL migration guards ---------------------------------------------------------
SQL = (ROOT / "supabase" / "migrations" / "0002_polygon_ids_storage_publishing.sql").read_text()


def test_every_new_table_has_rls_and_no_anon_write():
    tables = re.findall(r"CREATE TABLE IF NOT EXISTS public\.(\w+)", SQL)
    assert tables
    for t in tables:
        assert f"ALTER TABLE public.{t}" in SQL and "ENABLE ROW LEVEL SECURITY" in SQL
        assert re.search(rf"FOR SELECT TO anon, authenticated", SQL)
    assert re.search(r"REVOKE ALL ON .*FROM anon, authenticated", SQL)
    assert not re.search(r"GRANT (ALL|INSERT|UPDATE|DELETE)[^;]*TO[^;]*\banon\b", SQL)


def test_bucket_is_service_write_only():
    assert "TO service_role" in SQL.rsplit("drought-data service write", 1)[1]
    assert "FOR SELECT TO anon" in SQL.rsplit("drought-data public read", 1)[1]


def test_migration_defines_tables_before_functions_use_them():
    schema = (ROOT / "supabase" / "schema.sql").read_text()
    created = {m.group(1): m.start() for m in re.finditer(r"CREATE TABLE IF NOT EXISTS public\.(\w+)", SQL)}
    existing = set(re.findall(r"CREATE TABLE IF NOT EXISTS public\.(\w+)", schema))
    for m in re.finditer(r"CREATE (?:OR REPLACE )?FUNCTION public\.\w+.*?\$\$.*?\$\$;", SQL, re.S):
        for t in set(re.findall(r"(?:FROM|JOIN) public\.(\w+)", m.group(0))):
            assert t in existing or (t in created and created[t] < m.start()), \
                f"function at offset {m.start()} uses public.{t} before it exists"


def test_migration_runs_in_one_transaction_and_schema_policies_are_rerunnable():
    assert SQL.lstrip().split("\n")[-1].strip() == "COMMIT;" or SQL.rstrip().endswith("COMMIT;")
    assert "BEGIN;" in SQL
    schema = (ROOT / "supabase" / "schema.sql").read_text()
    assert len(re.findall(r"CREATE POLICY", schema)) == len(re.findall(r"DROP POLICY IF EXISTS", schema))
