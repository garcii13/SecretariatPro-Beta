from pathlib import Path


def test_mutable_overlay_files_are_not_served_with_fileresponse():
    source = Path('secretariat_api/main.py').read_text(encoding='utf-8')
    assert 'app.mount("/scores"' not in source
    assert '@app.get("/scores/{filename}")' in source
    assert 'async def overlay_data() -> JSONResponse' in source
    assert 'FileResponse(runtime.paths.data_file' not in source


def test_score_store_uses_atomic_replace():
    source = Path('secretariat_core/ocr_store.py').read_text(encoding='utf-8')
    assert 'os.replace(temp_name, path)' in source
    assert 'self._lock = threading.RLock()' in source
