from __future__ import annotations

import base64
import io
import sys
import tempfile
import types
import unittest
from pathlib import Path

from PIL import Image

from secretariat_api.runtime import ApplicationRuntime

if "supabase" not in sys.modules:
    supabase_stub = types.ModuleType("supabase")
    supabase_stub.Client = object
    supabase_stub.create_client = lambda *_args, **_kwargs: None
    sys.modules["supabase"] = supabase_stub

from supabase_client import AVATAR_BUCKET, APP_SETTINGS_METADATA_KEY, ScoreboardSupabaseClient

ROOT = Path(__file__).resolve().parents[1]


class FakeUser:
    id = "operator-33"
    email = "operator@example.com"
    created_at = "2026-07-29T10:00:00Z"
    last_sign_in_at = "2026-07-29T12:00:00Z"
    user_metadata = {
        APP_SETTINGS_METADATA_KEY: {"language": "es"},
        "display_name": "Nombre anterior",
    }


class FakeAuth:
    def __init__(self, user):
        self.user = user
        self.payloads = []
        self.reset_email = ""

    def update_user(self, payload):
        self.payloads.append(payload)
        if "data" in payload:
            self.user.user_metadata = payload["data"]

        class Response:
            pass

        response = Response()
        response.user = self.user
        return response

    def reset_password_for_email(self, email):
        self.reset_email = email


class FakeQuery:
    def update(self, payload):
        self.payload = payload
        return self

    def eq(self, *_args):
        return self

    def execute(self):
        return types.SimpleNamespace(data=[])


class FakeBucket:
    def __init__(self):
        self.uploaded = None
        self.removed = None

    def upload(self, **kwargs):
        self.uploaded = kwargs
        return {"path": kwargs["path"]}

    def get_public_url(self, path):
        return f"https://project.supabase.co/storage/v1/object/public/avatars/{path}"

    def remove(self, paths):
        self.removed = paths


class FakeStorage:
    def __init__(self, bucket):
        self.bucket = bucket
        self.name = ""

    def from_(self, name):
        self.name = name
        return self.bucket


class FakeConnection:
    def __init__(self, user):
        self.auth = FakeAuth(user)
        self.bucket = FakeBucket()
        self.storage = FakeStorage(self.bucket)

    def table(self, _name):
        return FakeQuery()


class FakeAvatarAccount:
    user_id = "operator-33"
    user_email = "operator@example.com"

    def __init__(self):
        self.received = b""

    def upload_avatar(self, data, content_type):
        self.received = data
        self.content_type = content_type
        return {"display_name": "Operator", "avatar_url": "https://avatar"}


class Phase34Tests(unittest.TestCase):
    def client(self):
        client = ScoreboardSupabaseClient.__new__(ScoreboardSupabaseClient)
        client.user = FakeUser()
        client.client = FakeConnection(client.user)
        return client

    def test_account_panel_replaces_logged_user_stub(self):
        html = (ROOT / "webapp" / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="signed-out-account"', html)
        self.assertIn('id="forgot-password-button"', html)
        self.assertIn('id="account-panel"', html)
        self.assertIn('id="account-avatar-file"', html)
        self.assertIn('id="account-display-name"', html)
        self.assertIn('id="account-password-form"', html)
        self.assertNotIn('id="logged-user"', html)

    def test_account_api_routes_and_frontend_actions_exist(self):
        main = (ROOT / "secretariat_api" / "main.py").read_text(encoding="utf-8")
        js = (ROOT / "webapp" / "app.js").read_text(encoding="utf-8")
        for route in (
            '/api/auth/password-reset',
            '/api/account/profile',
            '/api/account/password',
            '/api/account/avatar',
        ):
            self.assertIn(route, main)
            self.assertIn(route, js)
        self.assertIn('Las contraseñas no coinciden.', js)
        self.assertIn('file.size > 8 * 1024 * 1024', js)

    def test_profile_metadata_preserves_app_settings(self):
        client = self.client()
        profile = client.update_user_profile("Paco García")
        self.assertEqual(profile["display_name"], "Paco García")
        metadata = client.user.user_metadata
        self.assertEqual(metadata["full_name"], "Paco García")
        self.assertEqual(metadata[APP_SETTINGS_METADATA_KEY]["language"], "es")

    def test_password_update_never_reads_or_returns_password(self):
        client = self.client()
        client.update_password("a-secure-password")
        self.assertEqual(client.client.auth.payloads[-1], {"password": "a-secure-password"})
        self.assertNotIn("password", client.user_profile())

    def test_avatar_uses_user_folder_and_auth_metadata(self):
        client = self.client()
        profile = client.upload_avatar(b"jpeg-data")
        self.assertEqual(client.client.storage.name, AVATAR_BUCKET)
        upload = client.client.bucket.uploaded
        self.assertEqual(upload["path"], "operator-33/profile.jpg")
        self.assertIsInstance(upload["file"], bytes)
        self.assertEqual(upload["file"], b"jpeg-data")
        self.assertEqual(upload["file_options"]["upsert"], "true")
        self.assertIn("operator-33/profile.jpg", profile["avatar_url"])
        self.assertEqual(client.user.user_metadata[APP_SETTINGS_METADATA_KEY]["language"], "es")

    def test_runtime_resizes_avatar_to_safe_jpeg(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = ApplicationRuntime(tmp)
            account = FakeAvatarAccount()
            runtime.supabase = account
            source = Image.new("RGBA", (1200, 600), (255, 0, 0, 170))
            buffer = io.BytesIO()
            source.save(buffer, format="PNG")
            data_url = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")
            result = runtime.upload_account_avatar(data_url)
            self.assertEqual(result["avatar_url"], "https://avatar")
            self.assertEqual(account.content_type, "image/jpeg")
            with Image.open(io.BytesIO(account.received)) as processed:
                self.assertEqual(processed.size, (512, 512))
                self.assertEqual(processed.mode, "RGB")

    def test_storage_setup_is_scoped_to_authenticated_user_folder(self):
        sql = (ROOT / "SUPABASE_PROFILE_SETUP.sql").read_text(encoding="utf-8")
        self.assertIn("'avatars'", sql)
        self.assertIn("auth.uid()::text", sql)
        self.assertIn("storage.foldername(name)", sql)
        self.assertIn("for insert", sql.lower())
        self.assertIn("for update", sql.lower())
        self.assertIn("for delete", sql.lower())

    def test_phase36_cache_and_version(self):
        app_html = (ROOT / "webapp" / "index.html").read_text(encoding="utf-8")
        overlay = (ROOT / "overlay.html").read_text(encoding="utf-8")
        tablet = (ROOT / "tablet" / "index.html").read_text(encoding="utf-8")
        main = (ROOT / "secretariat_api" / "main.py").read_text(encoding="utf-8")
        self.assertIn("styles.css?v=phase55", app_html)
        self.assertIn("app.js?v=phase36", app_html)
        self.assertIn("styles.css?v=phase57", overlay)
        self.assertIn("script.js?v=phase57", overlay)
        self.assertIn("tablet.css?v=phase74", tablet)
        self.assertIn("tablet.js?v=phase74", tablet)
        self.assertIn("36.0.0-alpha", main)


if __name__ == "__main__":
    unittest.main()
