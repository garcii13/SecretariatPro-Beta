import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from secretariat_api.runtime import ApplicationRuntime
from supabase_client import ScoreboardSupabaseClient


class WorkspaceLoginTests(unittest.TestCase):
    def test_workspace_context_does_not_repeat_membership_queries(self):
        client = object.__new__(ScoreboardSupabaseClient)
        workspace = {"id": "w", "role": "producer", "membership_status": "active"}
        client.list_workspaces = Mock(return_value=[workspace])
        client.activate_workspace = Mock(side_effect=AssertionError("Repeated lookup"))
        client.latest_workspace_subscription = Mock(return_value={"status": "active"})
        result = client.workspace_context("w")
        client.list_workspaces.assert_called_once()
        client.activate_workspace.assert_not_called()
        self.assertEqual(result["workspace"], workspace)
        self.assertEqual(client.active_membership["workspace_id"], "w")

    def test_sdk_transport_has_bounded_auth_and_network_timeouts(self):
        with patch.dict(os.environ, {"SUPABASE_URL": "https://example.invalid", "SUPABASE_PUBLISHABLE_KEY": "public-test-key"}), \
                patch("supabase_client.create_client") as create:
            ScoreboardSupabaseClient(interactive=True)
        transport = create.call_args.kwargs["options"].httpx_client
        try:
            self.assertEqual(transport.timeout.connect, 5)
            self.assertEqual(transport.timeout.read, 15)
        finally:
            transport.close()


class LoginReliabilityTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.runtime = ApplicationRuntime(self.folder.name)
        self.client = Mock(user_id="user", user_email="user@example.invalid")
        self.workspace = {"id": "workspace", "role": "producer"}
        self.client.login.return_value = self.client.user_email
        self.client.workspace_context.return_value = {
            "workspaces": [self.workspace], "workspace": self.workspace, "subscription": {"status": "active"},
        }
        self.client.published_visual_theme.return_value = {}
        self.client.ocr_consent.return_value = {"enabled": False, "can_manage": False}
        self.client.list_competitions.return_value = [{"id": "competition", "name": "League"}]
        self.client.user_app_settings.return_value = {}
        self.patch = patch("secretariat_api.runtime.ScoreboardSupabaseClient", return_value=self.client)
        self.patch.start()

    def tearDown(self):
        self.runtime._account_sync_pool.shutdown(wait=True)
        self.runtime.shutdown()
        self.patch.stop()
        self.folder.cleanup()

    def login(self):
        return self.runtime.login("user@example.invalid", "test-password")

    def test_success_does_not_immediately_validate_subscription_again(self):
        result = self.login()
        self.assertTrue(result["access"]["allowed"])
        self.runtime.refresh_subscription_access()
        self.client.latest_workspace_subscription.assert_not_called()
        self.assertEqual(self.runtime.available_competitions()[0]["id"], "competition")
        self.client.list_competitions.assert_called_once()

    def test_secondary_requests_run_concurrently(self):
        barrier = threading.Barrier(3)
        def response(value):
            def run():
                barrier.wait(timeout=2)
                return value
            return run
        self.client.published_visual_theme.side_effect = response({"id": "theme"})
        self.client.ocr_consent.side_effect = response({"enabled": True})
        self.client.list_competitions.side_effect = response([{"id": "competition"}])
        result = self.login()
        self.assertEqual(result["warnings"], [])
        self.assertEqual(self.runtime.published_theme["id"], "theme")
        self.assertTrue(self.runtime.ocr_consent["enabled"])

    def test_competition_outage_keeps_session_and_can_retry(self):
        self.client.list_competitions.side_effect = [TimeoutError("offline"), [{"id": "recovered"}]]
        result = self.login()
        self.assertTrue(result["warnings"])
        self.assertIs(self.runtime.supabase, self.client)
        self.assertTrue(self.runtime.production_access_allowed())
        self.assertEqual(self.runtime.available_competitions()[0]["id"], "recovered")

    def test_duplicate_submission_does_not_start_second_auth_request(self):
        self.runtime._login_lock.acquire()
        try:
            with self.assertRaises(BlockingIOError):
                self.login()
            self.client.login.assert_not_called()
        finally:
            self.runtime._login_lock.release()

    def test_bad_credentials_and_network_failure_are_distinct(self):
        error = RuntimeError("bad credentials")
        error.code = "invalid_credentials"
        self.client.login.side_effect = error
        with self.assertRaisesRegex(ValueError, "contraseña"):
            self.login()
        self.client.login.side_effect = TimeoutError("offline")
        with self.assertRaises(ConnectionError):
            self.login()
        self.assertIsNone(self.runtime.supabase)

    def test_logout_cancels_inflight_login(self):
        entered, release = threading.Event(), threading.Event()
        errors = []
        def theme():
            entered.set()
            release.wait(2)
            return {"id": "stale"}
        self.client.published_visual_theme.side_effect = theme
        def login():
            try:
                self.login()
            except Exception as exc:
                errors.append(exc)
        thread = threading.Thread(target=login)
        thread.start()
        try:
            self.assertTrue(entered.wait(1))
            self.runtime.logout()
        finally:
            release.set()
            thread.join(3)
        self.assertFalse(thread.is_alive())
        self.assertIsNone(self.runtime.supabase)
        self.assertEqual(len(errors), 1)
        self.assertNotEqual(self.runtime.published_theme.get("id"), "stale")

    def test_initial_cloud_settings_write_does_not_block_login(self):
        entered, release = threading.Event(), threading.Event()
        completed = threading.Event()
        results = []
        self.client.user_app_settings.return_value = None
        def save(settings):
            entered.set()
            release.wait(2)
        self.client.save_user_app_settings.side_effect = save
        def login():
            results.append(self.login())
            completed.set()
        thread = threading.Thread(target=login)
        thread.start()
        try:
            self.assertTrue(entered.wait(1))
            self.assertTrue(completed.wait(0.5), "Login waited for optional settings upload")
            self.assertTrue(results[0]["access"]["allowed"])
            self.assertFalse(release.is_set())
        finally:
            release.set()
            thread.join(3)

    def test_entitlement_outage_without_valid_cache_does_not_log_in(self):
        self.client.workspace_context.side_effect = TimeoutError("offline")
        with self.assertRaisesRegex(RuntimeError, "permiso offline"):
            self.login()
        self.assertIsNone(self.runtime.supabase)
        self.client.close.assert_called_once()

    def test_valid_offline_permission_skips_secondary_network_calls(self):
        self.runtime.subscription_store.save(user_id=self.client.user_id, workspace=self.workspace,
                                             subscription={"status": "active"}, access={"allowed": True})
        self.client.workspace_context.side_effect = TimeoutError("offline")
        result = self.login()
        self.assertTrue(result["access"]["allowed"])
        self.assertFalse(result["access"]["online_validation"])
        self.client.list_competitions.assert_not_called()
        self.client.published_visual_theme.assert_not_called()
        self.client.ocr_consent.assert_not_called()

    def test_stale_theme_cannot_overwrite_another_workspace(self):
        self.login()
        def theme(*args):
            self.runtime.active_workspace = {"id": "other"}
            return {"id": "stale"}
        self.client.published_visual_theme.side_effect = theme
        self.assertFalse(self.runtime.refresh_published_theme())
        self.assertNotEqual(self.runtime.published_theme.get("id"), "stale")
