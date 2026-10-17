const {test} = require('node:test');
const assert = require('node:assert/strict');
const Motion = require('../overlay_motion.js');

function element() {
  const animations = [], classes = new Set();
  const el = {dataset:{}, hidden:false, textContent:'2', classes, animations,
    classList:{contains:value=>classes.has(value)},
    querySelector(){return null;},querySelectorAll(){return [];},closest(){return null;},
    animate(frames,options) {
      let finish,reject;
      const animation={frames,options,finished:new Promise((yes,no)=>{finish=yes;reject=no;}),finish:()=>finish(),cancel:()=>reject(Error('cancelled'))};
      animations.push(animation);return animation;
    }};
  return el;
}
const drain=async()=>{await Promise.resolve();await Promise.resolve();};

test('frequent state polling never restarts the same entrance', () => {
  const node=element(),frames=[];
  const motion=new Motion({schedule:fn=>frames.push(fn)});
  motion.setVisible(node,true,'bottom');
  for(let i=0;i<20;i++) motion.setVisible(node,true,'bottom');
  assert.equal(frames.length,1);
  frames[0]();
  assert.equal(node.animations.length,1);
  assert.equal(node.dataset.spMotion,'on');
});
test('an exit completing after a new show cannot hide the new graphic', async () => {
  const node=element(),motion=new Motion({schedule:fn=>fn()});
  motion.setVisible(node,true,'bottom');
  motion.setVisible(node,false,'bottom');
  const oldExit=node.animations.at(-1);
  assert.equal(node.dataset.spMotion,'exiting');
  motion.setVisible(node,true,'bottom');
  oldExit.finish();
  await drain();
  assert.equal(node.dataset.spMotion,'on');
});
test('a hidden graphic settles after its short exit', async () => {
  const node=element(),motion=new Motion({schedule:fn=>fn()});
  motion.setVisible(node,true,'prematch');
  motion.setVisible(node,false,'prematch');
  assert.equal(node.animations.at(-1).options.duration,320);
  node.animations.at(-1).finish();
  await drain();
  assert.equal(node.dataset.spMotion,'off');
});
test('queued stale entrances cannot run after hiding or clearing', () => {
  const node=element(),frames=[],motion=new Motion({schedule:fn=>frames.push(fn)});
  motion.setVisible(node,true,'scoreboard');
  motion.setVisible(node,false,'scoreboard');
  frames[0]();
  assert.equal(node.animations.length,0);
  assert.equal(frames.length,1);
  motion.settle();
  assert.equal(node.animations.length,0);
  assert.equal(node.dataset.spMotion,'off');
});
test('reduced motion and unavailable animation API leave valid visibility', () => {
  const node=element(),motion=new Motion({reduced:()=>true,schedule:fn=>fn()});
  motion.setVisible(node,true,'standings');motion.setVisible(node,false,'standings');
  assert.equal(node.animations.length,0);assert.equal(node.dataset.spMotion,'off');
  node.animate=undefined;
  const legacy=new Motion({schedule:fn=>fn()});
  legacy.setVisible(node,true,'standings');legacy.setVisible(node,false,'standings');
  assert.equal(node.dataset.spMotion,'off');
});
test('score accents ignore initial and identical values without changing their text', () => {
  const node=element(),motion=new Motion({schedule:fn=>fn()});
  motion.scoreChanged(node,null,'2');motion.scoreChanged(node,'2','2');
  assert.equal(node.animations.length,0);
  motion.scoreChanged(node,'2','3');
  assert.equal(node.animations.length,1);assert.equal(node.textContent,'2');
});
test('detail choreography is bounded and cancelled on hide', async () => {
  const node=element(),children=Array.from({length:50},element);
  node.querySelectorAll=()=>children;
  const motion=new Motion({schedule:fn=>fn()});
  motion.setVisible(node,true,'standings');
  assert.equal(children.filter(el=>el.animations.length).length,32);
  assert.ok(children.every(el=>el.animations.every(a=>a.options.delay<=346)));
  motion.setVisible(node,false,'standings');
  await drain();
  assert.equal(motion.states.get(node).details.size,0);
});
test('motion preference changes settle pending exits and preserve shown panels', async () => {
  let reduced=false;
  const node=element(),motion=new Motion({reduced:()=>reduced,schedule:fn=>fn()});
  motion.setVisible(node,true,'bottom');
  reduced=true;motion.settle();
  await drain();
  assert.equal(node.dataset.spMotion,'on');
  motion.setVisible(node,false,'bottom');
  assert.equal(node.dataset.spMotion,'off');
});


test('a cancelled penalty exit cannot remove a penalty that has reappeared', async () => {
  const fs=require('node:fs'),vm=require('node:vm');
  const source=fs.readFileSync('script.js','utf8');
  const start=source.indexOf('  function animateStatusExit(');
  const end=source.indexOf('  function buildStatusNode(',start);
  const c={motionPreference:{matches:false},statusSlideOffset:()=>'-24px'};
  vm.runInNewContext(source.slice(start,end),c);
  const node=element();node.isConnected=true;
  let removed=0;node.remove=()=>removed++;
  c.animateStatusExit(node,'team1');
  assert.equal(node.dataset.spExiting,'1');
  node.dataset.spExiting='0';node.animations[0].cancel();
  await drain();
  assert.equal(removed,0);
});


test('reversing a transition starts at its current visible position', () => {
  const node=element();
  const sampled={filter:'opacity(0.37)',translate:'0px 9px'};
  const motion=new Motion({schedule:fn=>fn(),sample:()=>sampled});
  motion.setVisible(node,true,'bottom');
  motion.setVisible(node,false,'bottom');
  assert.deepEqual(node.animations.at(-1).frames[0],sampled);
  motion.setVisible(node,true,'bottom');
  assert.deepEqual(node.animations.at(-1).frames[0],sampled);
});
test('the goal handoff can seek its detail reveal for a late phase update', () => {
  const node=element(),child=element();node.querySelectorAll=()=>[child];
  const motion=new Motion({schedule:fn=>fn()});
  node.classes.add('goal-intro');
  motion.setVisible(node,true,'bottom');
  motion.revealDetails(node,'bottom','.bottom-scorer-row',{duration:480,start:-180,stagger:40,distance:7});
  assert.equal(child.animations[0].options.delay,-180);
  assert.equal(child.animations[0].options.duration,480);
});
