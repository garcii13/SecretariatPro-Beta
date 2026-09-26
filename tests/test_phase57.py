from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_status_html_has_empty_isolated_stacks_only():
    html=(ROOT/'overlay.html').read_text(encoding='utf-8')
    assert '<div class="sp-team-status-stack sp-team-status-stack--home" id="team1-status-stack"' in html
    assert '<div class="sp-team-status-stack sp-team-status-stack--away" id="team2-status-stack"' in html
    assert 'powerplay-team' not in html

def test_status_animation_cannot_leave_fill_state_stuck():
    js=(ROOT/'script.js').read_text(encoding='utf-8')
    assert 'function animateStatusEntry' in js
    assert 'fill: "none"' in js
    assert 'function animateStatusExit' in js
    assert 'animation.finished.then(done).catch(done)' in js
    assert 'data-sp-exiting' in js

def test_status_exit_collapses_layout_and_does_not_reorder_during_exit():
    css=(ROOT/'styles.css').read_text(encoding='utf-8')
    js=(ROOT/'script.js').read_text(encoding='utf-8')
    assert 'flex: 0 0 auto !important;' in css
    assert 'height: "0px"' in js
    assert 'maxHeight: "0px"' in js
    assert 'reorderStatusNodesWhenStable' in js
    assert 'if (hasExiting) return;' in js

def test_single_item_is_always_bottom_item():
    js=(ROOT/'script.js').read_text(encoding='utf-8')
    assert 'nodes[nodes.length - 1].classList.add("sp-status-item--bottom")' in js

def test_blink_is_on_content_not_box():
    css=(ROOT/'styles.css').read_text(encoding='utf-8')
    assert '.sp-status-item--ending .sp-status-item__content' in css
    assert '@keyframes spStatusContentBlink57' in css
