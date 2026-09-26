from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_overlay_cache_bust_tracks_latest_component():
    html=(ROOT/'overlay.html').read_text(encoding='utf-8')
    assert 'styles.css?v=phase57' in html
    assert 'script.js?v=phase57' in html

def test_old_phase56_component_is_not_used_by_overlay():
    html=(ROOT/'overlay.html').read_text(encoding='utf-8')
    js=(ROOT/'script.js').read_text(encoding='utf-8')
    assert 'id="team1-powerplay"' not in html
    assert 'id="team2-powerplay"' not in html
    assert 'setStatusElementActive' not in js

def test_new_component_has_explicit_bottom_only_geometry():
    css=(ROOT/'styles.css').read_text(encoding='utf-8')
    block=css.split('PHASE 57 — ISOLATED SCOREBOARD STATUS COMPONENT',1)[1]
    assert 'border-top-left-radius: 0 !important;' in block
    assert 'border-top-right-radius: 0 !important;' in block
    assert '.sp-status-item.sp-status-item--bottom' in block
    assert 'border-bottom-left-radius: 13px !important;' in block
    assert 'border-bottom-right-radius: 13px !important;' in block
