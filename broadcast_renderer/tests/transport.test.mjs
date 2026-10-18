import { test } from 'node:test';
import assert from 'node:assert/strict';
import { harness, fixture } from './harness.mjs';

test('initial load and polling cannot overlap or restore a cancelled graphic with an older response', async () => {
  const h = await harness();
  try {
    const pending=[];
    h.w.fetch = path => {
      if (String(path).includes('data.json')) return new Promise(resolve=>pending.push(resolve));
      return Promise.resolve({ok:true,text:async()=> '2'});
    };
    const poll=h.intervals.find(i=>i.ms===250).callback;
    poll(); await h.flush(); poll(); await h.flush();
    assert.equal(pending.length,1,'only one state request may be active');
    const cancelled=fixture(); cancelled.animation.status='hide'; cancelled.bottombar.status='hide';
    cancelled.broadcast_flow={generation:9,phase:'IDLE'};
    cancelled.overlay_transport={epoch:'one',revision:2,context:'match-b',scores:{team1_score:'5',team2_score:'4',time:'22:03'}};
    pending.shift()({ok:true,json:async()=>cancelled}); await h.flush();
    assert.equal(h.w.document.querySelector('.team1-score').value,'5');
    assert.ok(h.w.document.getElementById('scoreboard-wrapper').classList.contains('hidden'));
    assert.equal(h.w.document.getElementById('bottom-bar').classList.contains('show'),false);
    poll(); await h.flush();
    const older=fixture(); older.overlay_transport={epoch:'one',revision:1,scores:{team1_score:'3'}};
    pending.shift()({ok:true,json:async()=>older}); await h.flush();
    assert.equal(h.w.document.querySelector('.team1-score').value,'5');
    assert.ok(h.w.document.getElementById('scoreboard-wrapper').classList.contains('hidden'));
  } finally {h.close();}
});

test('embedded raw score snapshot needs no TXT requests; server restart and match switch remain usable', async () => {
  const data=fixture(); data.overlay_transport={epoch:'first',revision:90,context:'a',scores:{team1_score:'7',team2_score:'6',time:'18:20'}};
  const h=await harness({state:data});
  try {
    assert.equal(h.w.document.querySelector('.team1-score').value,'7');
    assert.equal(h.requests.filter(path=>path.includes('.txt')).length,0);
    const next=fixture(); next.team1.name='New match';
    next.overlay_transport={epoch:'restarted',revision:1,context:'b',scores:{team1_score:'0',team2_score:'0',time:'00:00'}};
    await h.update(next);
    assert.equal(h.w.document.querySelector('.team1-name').value,'New match');
    assert.equal(h.w.document.querySelector('.team1-score').value,'0');
  } finally {h.close();}
});

test('HTTP failures, rejected TXT fetches and invalid score content preserve the last valid value', async () => {
  const h=await harness();
  try {
    const poll=h.intervals.find(i=>i.ms===250).callback;
    h.w.fetch=async path=>String(path).includes('data.json')
      ? {ok:true,json:async()=>fixture()}
      : String(path).includes('Home Score') ? {ok:false,text:async()=>'<h1>Error</h1>'}
      : String(path).includes('Away Score') ? Promise.reject(new Error('offline'))
      : {ok:true,text:async()=>''};
    await poll(); await h.flush();
    assert.equal(h.w.document.querySelector('.team1-score').value,'3');
    assert.equal(h.w.document.querySelector('.team2-score').value,'2');
    assert.equal(h.w.document.getElementById('match-time').textContent,'15:20');
    h.w.fetch=async()=>({ok:false,json:async()=>({})});
    await poll(); await h.flush();
    assert.equal(h.w.document.querySelector('.team1-score').value,'3');
  } finally {h.close();}
});
