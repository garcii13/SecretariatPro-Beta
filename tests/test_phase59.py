from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_ocr_samples_have_retry_outbox_and_diagnostics():
    runtime = (ROOT / 'secretariat_api' / 'runtime.py').read_text(encoding='utf-8')
    assert 'ocr_sample_outbox' in runtime
    assert 'def _flush_ocr_sample_outbox_once' in runtime
    assert 'def ocr_sample_delivery_status' in runtime
    assert 'last_error' in runtime


def test_sample_upload_errors_are_not_silently_discarded_anymore():
    runtime = (ROOT / 'secretariat_api' / 'runtime.py').read_text(encoding='utf-8')
    assert 'self._queue_ocr_sample(payload' in runtime
    assert 'SecretariatPro-OCR-Sample-Retry' in runtime


def test_live_exposes_delivery_diagnostic():
    html = (ROOT / 'webapp' / 'index.html').read_text(encoding='utf-8')
    js = (ROOT / 'webapp' / 'app.js').read_text(encoding='utf-8')
    assert 'settings-ocr-delivery-status' in html
    assert 'ocr_sample_delivery' in js
    assert 'pendiente(s) de reintento' in js


def test_stopping_ocr_does_not_close_selected_camera():
    api = (ROOT / 'secretariat_api' / 'main.py').read_text(encoding='utf-8')
    block = api.split('@app.post("/api/ocr/stop")', 1)[1].split('@app.get("/api/ocr/status")', 1)[0]
    assert 'runtime.ocr_runtime.stop' in block
    assert 'camera_service.close' not in block


def test_repair_sql_is_bundled_and_private():
    sql = (ROOT / 'SUPABASE_OCR_LAB_REPAIR.sql').read_text(encoding='utf-8')
    assert "'ocr-training-samples'" in sql
    assert 'public = false' in sql
    assert 'sp_ocr_samples_opt_in_insert' in sql
    assert 'ocr_training_samples_opt_in_insert' in sql
