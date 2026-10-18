import { test } from 'node:test';
import assert from 'node:assert/strict';
import { fixture, harness } from './harness.mjs';

async function setup() {
  const h = await harness({ reduced: false });
  const queue = [];
  let reduced = false;
  const motion = new h.w.SPBroadcastMotion({ schedule: fn => queue.push(fn), reduced: () => reduced });
  const node = h.w.document.createElement('div');
  node.className = 'stats-modal';
  node.innerHTML = '<div class="stats-panel"><div class="stats-header">TITLE</div><div class="standings-row">ROW</div></div>';
  h.w.document.body.append(node);
  const frame = () => { for (const fn of queue.splice(0)) fn(); };
  const finish = () => { for (const state of motion.states.values()) { state.animation?.progress(1); state.details?.progress(1); } };
  return { h, motion, node, frame, finish, reduce: value => { reduced = value; motion.settle(); }, close: () => { motion.settle(); h.close(); } };
}

test('repeated polling does not restart GSAP entrances and interrupted exits cannot hide a new show', async () => {
  const s = await setup();
  try {
    const { motion, node, frame } = s;
    motion.setVisible(node,true,'standings'); frame();
    const state = motion.states.get(node), first = state.animation;
    first.progress(.5);
    for (let i=0;i<12;i++) motion.setVisible(node,true,'standings');
    assert.equal(state.animation,first);
    motion.setVisible(node,false,'standings'); frame();
    const exit = state.animation; exit.progress(.4);
    const position = state.value.y, alpha = state.value.alpha;
    motion.setVisible(node,true,'standings');
    assert.equal(state.value.y,position); assert.equal(state.value.alpha,alpha);
    frame(); s.finish();
    exit.progress(1);
    assert.equal(node.dataset.spMotion,'on');
    assert.equal(state.surface.style.translate,'');
    assert.equal(state.surface.style.filter,'');
    assert.deepEqual(s.h.errors,[]);
  } finally { s.close(); }
});

test('a queued entrance is cancelled before its first frame and reduced motion settles every graphic', async () => {
  const s = await setup();
  try {
    s.motion.setVisible(s.node,true,'standings');
    s.motion.setVisible(s.node,false,'standings'); s.frame();
    assert.equal(s.node.dataset.spMotion,'off');
    assert.equal(s.motion.states.get(s.node).animation,undefined);
    s.motion.setVisible(s.node,true,'standings'); s.frame(); s.finish();
    s.motion.setVisible(s.node,false,'standings'); s.frame(); s.reduce(true);
    assert.equal(s.node.dataset.spMotion,'off');
    s.motion.setVisible(s.node,true,'standings');
    assert.equal(s.node.dataset.spMotion,'on');
    assert.equal(s.motion.states.get(s.node).surface.style.filter,'');
  } finally { s.close(); }
});

test('clock ticks and initial scores never trigger score animations', async () => {
  const s = await setup();
  try {
    const input = s.h.w.document.createElement('input'); input.value='4';
    s.motion.scoreChanged(input,null,'4'); s.motion.scoreChanged(input,'4','4');
    assert.equal(s.motion.states.has(input),false);
    s.motion.scoreChanged(input,'3','4');
    s.motion.states.get(input).animation.progress(1);
    assert.equal(input.value,'4'); assert.equal(input.style.filter,'');
  } finally { s.close(); }
});

test('the vector goal timeline seeks server time, transitions to scorer, freezes on cancel and restarts by generation', async () => {
  const s = await setup();
  try {
    const node = s.h.w.document.getElementById('bottom-bar');
    const phase = {phase:'GOAL_INTRO',key:'7:GOAL_INTRO',overlay:true,reveal:false,elapsed:1.1,duration:2.2};
    node.classList.add('goal-intro');
    s.motion.presentGoal(node,phase,true);
    const intro = s.motion.goals.get(node);
    assert.ok(Math.abs(intro.timeline.time()-1.1)<.03);
    s.motion.presentGoal(node,phase,true);
    assert.equal(s.motion.goals.get(node),intro);
    s.motion.presentGoal(node,phase,false);
    assert.equal(intro.timeline.paused(),true);
    assert.equal(node.classList.contains('goal-intro'),true);
    s.motion.presentGoal(node,{...phase,key:'8:GOAL_INTRO',elapsed:0},true);
    assert.notEqual(s.motion.goals.get(node),intro);
    node.classList.add('goal-reveal');
    s.motion.presentGoal(node,{...phase,phase:'GOAL_REVEAL',key:'8:GOAL_REVEAL',reveal:true,elapsed:.32,duration:.64},true);
    const reveal = s.motion.goals.get(node);
    assert.ok(Math.abs(reveal.timeline.duration()-.64)<.001);
    reveal.timeline.progress(1);
    assert.equal(node.querySelector('.bottom-goal-intro').style.getPropertyValue('--studio-goal-cut'),'100%');
    node.classList.remove('goal-intro','goal-reveal');
    s.motion.presentGoal(node,{...phase,phase:'GOAL_BOTTOM',key:'8:GOAL_BOTTOM',overlay:false,elapsed:0},true);
    assert.equal(node.querySelector('.bottom-goal-intro').style.getPropertyValue('--studio-goal-cut'),'');
    assert.equal(node.querySelector('#bottom-scorer-name').textContent,'García');
    assert.deepEqual(s.h.errors,[]);
  } finally { s.close(); }
});

test('a returning penalty cancels GSAP removal and reduced motion completes pending removals', async () => {
  const s = await setup();
  try {
    const node = s.h.w.document.createElement('div'); node.textContent='1:25';
    s.h.w.document.body.append(node);
    let removed = 0;
    s.motion.statusEnter(node,'team1');
    s.motion.statuses.get(node).tween.progress(1);
    s.motion.statusExit(node,'team1',()=>removed++);
    const old = s.motion.statuses.get(node).tween; old.progress(.5);
    s.motion.cancelStatus(node,'team1');
    s.motion.statuses.get(node).tween.progress(1); old.progress(1);
    assert.equal(removed,0); assert.equal(node.style.filter,'');
    s.motion.statusExit(node,'team2',()=>removed++); s.reduce(true);
    assert.equal(removed,1); assert.equal(s.motion.statuses.size,0);
  } finally { s.close(); }
});

test('goal phase classes follow BroadcastFlow cancellation and accept a new event without stale content', async () => {
  const state = fixture();
  state.broadcast_flow={phase:'GOAL_INTRO',generation:4,started_at:Date.now()/1000-.3,duration_seconds:2.2};
  const h = await harness({ state, reduced:false });
  try {
    const bottom = h.w.document.getElementById('bottom-bar');
    assert.ok(bottom.classList.contains('goal-intro'));
    assert.equal(bottom.dataset.goalKey,'4:GOAL_INTRO');
    state.broadcast_flow={phase:'CANCELLED',generation:5};state.bottombar.status='hide';
    await h.update(state);
    assert.ok(bottom.classList.contains('goal-intro'),'curtain survives until outro');
    state.broadcast_flow={phase:'GOAL_INTRO',generation:6};state.bottombar.status='show';state.bottombar.scorer_last_name='Nuevo';
    await h.update(state);
    assert.equal(bottom.dataset.goalKey,'6:GOAL_INTRO');
    state.broadcast_flow={phase:'GOAL_REVEAL',generation:6,duration_seconds:.64};
    await h.update(state);
    assert.ok(bottom.classList.contains('goal-reveal'));
    state.broadcast_flow={phase:'GOAL_BOTTOM',generation:6,duration_seconds:8};
    await h.update(state);
    assert.equal(bottom.classList.contains('goal-intro'),false);
    assert.equal(h.w.document.getElementById('bottom-scorer-name').textContent,'Nuevo');
    assert.deepEqual(h.errors,[]);
  } finally { h.close(); }
});

test('lower thirds animate content while their connected painted drawers stay fixed', async () => {
  const h = await harness({reduced:true});
  const motion = new h.w.SPBroadcastMotion({reduced:()=>false,schedule:fn=>fn()});
  try {
    for (const [id,kind,containers,content] of [
      ['bottom-bar','bottom',['.bottom-team-block','.bottom-match-state','.bottom-event-copy'],'.bottom-current-score'],
      ['player-profile-bar','profile',['.player-profile-main','.player-profile-stats'],'.player-profile-stats b'],
    ]) {
      const node = h.w.document.getElementById(id);
      motion.setVisible(node,true,kind);
      const state = motion.states.get(node);
      state.details.pause(0);
      for (const selector of containers) {
        const drawer = node.querySelector(selector);
        assert.equal(drawer.style.filter,'',`${selector} must remain part of the continuous background`);
        assert.equal(drawer.style.translate,'',`${selector} must not open gaps`);
      }
      assert.notEqual(node.querySelector(content).style.filter,'');
      assert.ok(state.details.duration() <= .81,'connected content enters as a compact group');
      state.details.progress(.4);
      assert.match(node.querySelector(content).style.translate,/0px /);
      state.details.progress(1);
      assert.equal(node.querySelector(content).style.filter,'');
    }
    assert.deepEqual(h.errors,[]);
  } finally {motion.settle();h.close();}
});

test('GOL handoff carries the visible artwork pose without rewinding, and a different goal uses its own pose', async () => {
  const s = await setup();
  try {
    const node = s.h.w.document.getElementById('bottom-bar');
    node.classList.add('goal-intro');
    const phase = {phase:'GOAL_INTRO',key:'21:GOAL_INTRO',overlay:true,reveal:false,elapsed:.7,duration:2.2};
    s.motion.presentGoal(node,phase,true);
    s.motion.goals.get(node).timeline.pause(.7);
    const echo = node.querySelector('.studio-goal-echo'), word = node.querySelector('#bottom-goal-word');
    const x = parseFloat(echo._gsap.x), opacity = echo.style.opacity, wordX = parseFloat(word._gsap.x);
    s.motion.presentGoal(node,{...phase,phase:'GOAL_REVEAL',key:'21:GOAL_REVEAL',reveal:true,elapsed:0,duration:.64},true);
    s.motion.goals.get(node).timeline.pause(0);
    assert.ok(Math.abs(parseFloat(echo._gsap.x)-x)<.01,'echo continues from its visible position');
    assert.ok(Math.abs(parseFloat(word._gsap.x)-wordX)<.01,'word never snaps to its rest position');
    assert.equal(echo.style.opacity,opacity);
    s.motion.presentGoal(node,{...phase,key:'22:GOAL_INTRO'},true);
    s.motion.goals.get(node).timeline.pause(.7);
    s.motion.presentGoal(node,{...phase,phase:'GOAL_REVEAL',key:'23:GOAL_REVEAL',reveal:true,elapsed:0,duration:.64},true);
    assert.equal(parseFloat(echo._gsap.x),-28,'a different generation cannot inherit the previous event pose');
    assert.deepEqual(s.h.errors,[]);
  } finally {s.close();}
});

test('reduced-motion goal handoff uses a fade and clears its mask state for the following event', async () => {
  const h = await harness({reduced:true});
  const motion = new h.w.SPBroadcastMotion({reduced:()=>true});
  try {
    const node = h.w.document.getElementById('bottom-bar'), curtain = node.querySelector('.bottom-goal-intro');
    motion.presentGoal(node,{phase:'GOAL_REVEAL',key:'30:GOAL_REVEAL',overlay:true,reveal:true,elapsed:0,duration:.64},true);
    motion.goals.get(node).timeline.progress(1);
    assert.equal(curtain.style.getPropertyValue('--studio-goal-opacity'),'0');
    assert.equal(curtain.style.getPropertyValue('--studio-goal-cut'),'','reduced motion never moves the curtain');
    motion.presentGoal(node,{phase:'GOAL_BOTTOM',key:'30:GOAL_BOTTOM',overlay:false,reveal:false,elapsed:0,duration:8},true);
    assert.equal(curtain.style.getPropertyValue('--studio-goal-opacity'),'');
    assert.deepEqual(h.errors,[]);
  } finally {motion.settle();h.close();}
});

test('scoreboard slides in and out above the viewport as one opaque piece, including current powerplay queues', async () => {
  const h = await harness({reduced:true}), queue=[];
  const motion = new h.w.SPBroadcastMotion({reduced:()=>false,schedule:fn=>queue.push(fn)});
  try {
    const node=h.w.document.getElementById('scoreboard-wrapper');
    let queueBottom=318;
    const y=()=>motion.states.get(node)?.value.y || 0;
    const rect=(top,bottom)=>({top:top+y(),bottom:bottom+y(),height:bottom-top,width:1080,left:0,right:1080,x:0,y:top+y()});
    node.getBoundingClientRect=()=>rect(48,180);
    node.querySelector('.scoreboard').getBoundingClientRect=()=>rect(48,142);
    node.querySelector('.time-box').getBoundingClientRect=()=>rect(142,190);
    for(const stack of node.querySelectorAll('.sp-team-status-stack')) stack.getBoundingClientRect=()=>rect(142,queueBottom);
    motion.setVisible(node,true,'scoreboard');
    assert.equal(motion.states.get(node).surface,node,'the entire wrapper, including statuses, shares the slide');
    queueBottom=450; // State adapter populates additional sanctions before the first scheduled frame.
    queue.splice(0).forEach(fn=>fn());
    const state=motion.states.get(node);
    assert.equal(state.value.y,-474);
    assert.equal(state.value.alpha,1);
    assert.equal(node.style.filter,'');
    assert.equal(state.details,undefined,'no separate text introduction');
    for(const selector of ['.center','.team1-name-box','.team2-name-box','.score-input','.score-box','.clock-content']) {
      for(const part of node.querySelectorAll(selector)) {
        assert.equal(part.style.filter,'');assert.equal(part.style.translate,'',selector);
      }
    }
    state.animation.progress(.5);
    assert.equal(state.value.alpha,1,'text stays fully opaque during the slide');
    const score=node.querySelector('.team1-score');
    motion.scoreChanged(score,'3','4');
    assert.equal(motion.states.has(score),false,'live score updates do not dim or move the text');
    motion.revealDetails(node,'scoreboard');
    assert.equal(state.details,undefined,'an explicit detail request cannot stage scoreboard text');
    state.animation.progress(1);
    motion.setVisible(node,false,'scoreboard');queue.splice(0).forEach(fn=>fn());
    state.animation.progress(.5);
    assert.ok(state.value.y<0,'outro moves upwards');assert.equal(state.value.alpha,1);
    state.animation.progress(.999);
    assert.ok(queueBottom+state.value.y<0,'including all absolute status rows');
    state.animation.progress(1);
    assert.equal(node.dataset.spMotion,'off');assert.equal(node.style.translate,'');
    assert.deepEqual(h.errors,[]);
  } finally {motion.settle();h.close();}
});

test('bottom outro fades at a fixed position and retains unfinished content until it is hidden', async () => {
  const h=await harness({reduced:true}), queue=[];
  const motion=new h.w.SPBroadcastMotion({reduced:()=>false,schedule:fn=>queue.push(fn)});
  try {
    const node=h.w.document.getElementById('bottom-bar');
    motion.setVisible(node,true,'bottom');queue.splice(0).forEach(fn=>fn());
    const state=motion.states.get(node);
    state.animation.pause().progress(.35);state.details.pause(.2);
    const content=node.querySelector('.bottom-scorer-row');
    const frozen={filter:content.style.filter,translate:content.style.translate}, entryY=state.value.y;
    motion.setVisible(node,false,'bottom');
    assert.deepEqual({filter:content.style.filter,translate:content.style.translate},frozen,'no snap when hiding mid-entrance');
    queue.splice(0).forEach(fn=>fn());
    state.animation.progress(.5);
    assert.equal(state.value.y,entryY,'outro never nudges the bottom down');
    assert.deepEqual({filter:content.style.filter,translate:content.style.translate},frozen);
    state.animation.progress(1);
    assert.equal(node.dataset.spMotion,'off');
    assert.equal(content.style.filter,'');assert.equal(content.style.translate,'');
    motion.setVisible(node,true,'bottom');queue.splice(0).forEach(fn=>fn());
    state.animation.progress(1);state.details.progress(1);
    motion.setVisible(node,false,'bottom');queue.splice(0).forEach(fn=>fn());
    for(const progress of [.1,.5,.9]) {state.animation.progress(progress);assert.equal(state.value.y,0);}
    state.animation.progress(1);
    assert.equal(node.dataset.spMotion,'off');assert.deepEqual(h.errors,[]);
  } finally {motion.settle();h.close();}
});

test('returning during a bottom outro resumes the same content pose without restarting its entrance', async () => {
  const h=await harness({reduced:true}), queue=[];
  const motion=new h.w.SPBroadcastMotion({reduced:()=>false,schedule:fn=>queue.push(fn)});
  try {
    const node=h.w.document.getElementById('bottom-bar');
    motion.setVisible(node,true,'bottom');queue.splice(0).forEach(fn=>fn());
    const state=motion.states.get(node);
    state.animation.pause().progress(.4);state.details.pause(.2);
    const details=state.details, content=node.querySelector('.bottom-scorer-row');
    motion.setVisible(node,false,'bottom');queue.splice(0).forEach(fn=>fn());
    const exit=state.animation;exit.progress(.3);
    const pose={filter:content.style.filter,translate:content.style.translate};
    motion.setVisible(node,true,'bottom');queue.splice(0).forEach(fn=>fn());
    assert.equal(state.details,details);assert.equal(details.paused(),false);
    assert.deepEqual({filter:content.style.filter,translate:content.style.translate},pose);
    state.animation.progress(1);details.progress(1);exit.progress(1);
    assert.equal(node.dataset.spMotion,'on');assert.equal(content.style.filter,'');
    assert.deepEqual(h.errors,[]);
  } finally {motion.settle();h.close();}
});
