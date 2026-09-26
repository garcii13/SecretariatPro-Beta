from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_live_uses_rpc_not_direct_sample_table_insert():
    src=(ROOT/'supabase_client.py').read_text(encoding='utf-8')
    block=src.split('def upload_ocr_sample',1)[1].split('# ------------------------------------------------------------------\n    # SecretariatPro Manager',1)[0]
    assert 'rpc("sp_submit_ocr_sample"' in block
    assert 'rpc("sp_find_ocr_sample"' in block
    assert '"upsert": "false"' in block
    assert '/dedupe/' in block
    assert 'table("sp_ocr_samples").insert' not in block

def test_sql_revokes_client_read_and_direct_insert():
    sql=(ROOT/'SUPABASE_OCR_LAB_RPC_FIX_V3.sql').read_text(encoding='utf-8')
    assert 'create or replace function public.sp_submit_ocr_sample' in sql
    assert 'create or replace function public.sp_find_ocr_sample' in sql
    assert 'security definer' in sql.lower()
    assert 'revoke select, insert, update, delete on public.sp_ocr_samples from authenticated' in sql
    assert 'grant execute on function public.sp_submit_ocr_sample' in sql
