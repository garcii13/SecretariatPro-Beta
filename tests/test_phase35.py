from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from secretariat_core.subscription_store import SubscriptionAccessStore, evaluate_subscription

BASE = Path(__file__).resolve().parents[1]


class Phase35SubscriptionTests(unittest.TestCase):
    def sample_subscription(self) -> dict:
        now = datetime(2026, 7, 29, 16, 0, tzinfo=timezone.utc)
        return {
            "id": "sub-1",
            "plan_id": "association_test",
            "status": "active",
            "starts_at": (now - timedelta(days=10)).isoformat(),
            "ends_at": (now + timedelta(days=300)).isoformat(),
            "retention_until": (now + timedelta(days=1030)).isoformat(),
            "offline_grace_days": 4,
            "plan": {"id": "association_test", "name": "Asociación de pruebas", "entitlements": {"bulk_import": True}},
        }

    def test_offline_grace_is_exactly_four_days(self):
        validated = datetime(2026, 7, 29, 16, 0, tzinfo=timezone.utc)
        subscription = self.sample_subscription()
        allowed = evaluate_subscription(
            subscription,
            validated_at=validated,
            now=validated + timedelta(days=3, hours=23, minutes=59),
            online=False,
        )
        blocked = evaluate_subscription(
            subscription,
            validated_at=validated,
            now=validated + timedelta(days=4, seconds=1),
            online=False,
        )
        self.assertTrue(allowed["production_allowed"])
        self.assertEqual(allowed["mode"], "offline_grace")
        self.assertFalse(blocked["production_allowed"])

    def test_expired_subscription_is_manager_read_only_during_retention(self):
        now = datetime(2026, 7, 29, 16, 0, tzinfo=timezone.utc)
        subscription = self.sample_subscription()
        subscription.update({
            "status": "expired",
            "ends_at": (now - timedelta(days=1)).isoformat(),
            "retention_until": (now + timedelta(days=730)).isoformat(),
        })
        access = evaluate_subscription(subscription, now=now, online=True)
        self.assertFalse(access["production_allowed"])
        self.assertTrue(access["manager_read_only"])
        self.assertEqual(access["mode"], "read_only")

    def test_cache_is_scoped_to_the_authenticated_user(self):
        with tempfile.TemporaryDirectory() as folder:
            store = SubscriptionAccessStore(Path(folder) / "subscription_access.json")
            subscription = self.sample_subscription()
            workspace = {"id": "workspace-1", "name": "Asociación", "role": "owner"}
            store.save(user_id="user-a", workspace=workspace, subscription=subscription, access={"allowed": True})
            cached_workspace, cached_access = store.offline_access(user_id="user-a")
            wrong_workspace, wrong_access = store.offline_access(user_id="user-b")
            self.assertEqual(cached_workspace["id"], "workspace-1")
            self.assertTrue(cached_access["allowed"])
            self.assertEqual(wrong_workspace, {})
            self.assertFalse(wrong_access["allowed"])


class Phase35ArchitectureTests(unittest.TestCase):
    def test_subscription_gate_and_workspace_selector_exist(self):
        html = (BASE / "webapp" / "index.html").read_text(encoding="utf-8")
        js = (BASE / "webapp" / "app.js").read_text(encoding="utf-8")
        main = (BASE / "secretariat_api" / "main.py").read_text(encoding="utf-8")
        self.assertIn('id="subscription-gate"', html)
        self.assertIn('id="account-workspace-select"', html)
        self.assertIn("renderSubscriptionGate", js)
        self.assertIn("production_access_allowed", main)
        self.assertIn('status_code=402', main)
        self.assertIn('version="36.0.0-alpha"', main)

    def test_manager_is_a_separate_desktop_and_web_ready_frontend(self):
        self.assertTrue((BASE / "run_manager.py").exists())
        self.assertTrue((BASE / "manager_api" / "main.py").exists())
        html = (BASE / "manager_app" / "index.html").read_text(encoding="utf-8")
        self.assertIn("SecretariatPro Manager", html)
        self.assertIn("Importación masiva", html)
        self.assertIn("Usuarios y realizadores", html)
        self.assertIn("Identidad visual", html)
        self.assertNotIn("OBS WebSocket", html)

    def test_sql_grants_test_account_association_and_retention(self):
        sql = (BASE / "SUPABASE_PHASE35_MULTI_TENANT.sql").read_text(encoding="utf-8")
        self.assertIn("a.garciarenones%", sql)
        self.assertIn("'association'", sql)
        self.assertIn("'owner'", sql)
        self.assertIn("offline_grace_days", sql)
        self.assertIn("default 4", sql.lower())
        self.assertIn("interval '2 years'", sql.lower())
        self.assertIn("sp_import_jobs", sql)
        for entity in ("competition", "team", "player", "coach", "producer", "match", "result", "event", "visual_identity"):
            self.assertIn(f"'{entity}'", sql)

    def test_sports_queries_are_scoped_to_active_workspace(self):
        source = (BASE / "supabase_client.py").read_text(encoding="utf-8")
        self.assertIn('.eq("workspace_id", workspace_id)', source)
        self.assertIn('"workspace_id": str((self.active_workspace or {}).get("id")', source)
        self.assertIn("assignment_mode", source)


if __name__ == "__main__":
    unittest.main()
