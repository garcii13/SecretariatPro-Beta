from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from supabase_client import ScoreboardSupabaseClient


ROOT = Path(__file__).resolve().parents[1]


class FakeFunctions:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def invoke(self, name: str, options: dict) -> dict:
        self.calls.append((name, options))
        return {"ok": True, "invited": True, "status": "invited", "email": options["body"]["email"]}


class FakeCloud:
    def __init__(self) -> None:
        self.functions = FakeFunctions()


class TimeoutOnceFunctions(FakeFunctions):
    def invoke(self, name: str, options: dict) -> dict:
        self.calls.append((name, options))
        if len(self.calls) == 1:
            raise TimeoutError("The read operation timed out")
        return {"ok": True, "invited": False, "already_pending": True}


class BetaInvitationTests(unittest.TestCase):
    def test_manager_invites_through_authenticated_edge_function(self):
        client = ScoreboardSupabaseClient.__new__(ScoreboardSupabaseClient)
        client.client = FakeCloud()
        client.active_workspace = {"id": "workspace-1"}
        client.active_membership = {"role": "competition_manager"}
        result = client.manager_invite_member(" NEW@Example.com ", "producer")
        self.assertTrue(result["invited"])
        name, options = client.client.functions.calls[0]
        self.assertEqual(name, "invite-member")
        self.assertEqual(options["responseType"], "json")
        self.assertEqual(options["body"], {"workspace_id": "workspace-1", "email": "new@example.com", "role": "producer"})

    def test_profile_portal_url_uses_official_site_by_default_and_override_when_set(self):
        client = ScoreboardSupabaseClient.__new__(ScoreboardSupabaseClient)
        client.url = "https://project.supabase.co"
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(client.profile_portal_url(), "https://secretariatproapp.com/cuenta")
        with patch.dict(os.environ, {"SUPABASE_PROFILE_PORTAL_URL": "https://account.example.test"}, clear=True):
            self.assertEqual(client.profile_portal_url(), "https://account.example.test")

    @patch("supabase_client.time.sleep", return_value=None)
    def test_invitation_retries_one_transient_read_timeout(self, _sleep):
        client = ScoreboardSupabaseClient.__new__(ScoreboardSupabaseClient)
        client.client = FakeCloud()
        client.client.functions = TimeoutOnceFunctions()
        client.active_workspace = {"id": "workspace-1"}
        client.active_membership = {"role": "competition_manager"}

        result = client.manager_invite_member("new@example.com", "producer")

        self.assertTrue(result["recovered_from_timeout"])
        self.assertEqual(len(client.client.functions.calls), 2)

    def test_invitation_portal_and_security_migration_are_packaged(self):
        html = (ROOT / "manager_app" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "manager_app" / "app.js").read_text(encoding="utf-8")
        sql = (ROOT / "SUPABASE_BETA_INVITATIONS_AND_SECURITY.sql").read_text(encoding="utf-8").lower()
        invite = (ROOT / "supabase" / "functions" / "invite-member" / "index.ts").read_text(encoding="utf-8")
        portal = (ROOT / "website" / "src" / "scripts" / "account.ts").read_text(encoding="utf-8")
        account_page = (ROOT / "website" / "src" / "pages" / "cuenta.astro").read_text(encoding="utf-8")
        workflow = (ROOT / ".github" / "workflows" / "website.yml").read_text(encoding="utf-8")
        self.assertIn('data-view="profile"', html)
        self.assertIn('id="open-profile-portal"', html)
        self.assertIn('id="show-preflight"', (ROOT / "webapp" / "index.html").read_text(encoding="utf-8"))
        self.assertIn("/api/account/portal", js)
        self.assertIn("security_invoker = true", sql)
        self.assertIn("revoke all on public.competition_standings from anon", sql)
        self.assertIn("sp_accept_my_invitations", sql)
        self.assertIn("inviteUserByEmail", invite)
        self.assertIn("SUPABASE_SERVICE_ROLE_KEY", invite)
        self.assertIn("sp_has_workspace_role", invite)
        self.assertIn("updateUser({ password", portal)
        self.assertIn("AccountPortal", account_page)
        self.assertIn("npm run build", workflow)


if __name__ == "__main__":
    unittest.main()
