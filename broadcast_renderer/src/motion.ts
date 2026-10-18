import { gsap } from 'gsap';
import type { DetailOptions, GoalPhase, GraphicKind } from './types';

// A continuous acceleration curve at both ends avoids the initial kick and
// abrupt final deceleration of the previous independent drawer movements.
gsap.registerEase('studio.glide', progress => progress ** 3 * (progress * (progress * 6 - 15) + 10));
const ENTER = 'studio.glide';
const EXIT = 'studio.glide';
const SURFACES: Partial<Record<GraphicKind, string>> = {
  prematch: '.prematch-panel', lineups: '.lineups-panel',
  top_scorers: '.stats-panel', standings: '.stats-panel', penalties: '.penalties-panel',
};
const DETAILS: Partial<Record<GraphicKind, string>> = {
  bottom: '.bottom-team-block img,.bottom-match-time,.bottom-current-score,.bottom-scorer-row,.bottom-assistant-row',
  profile: '.player-profile-team-block img,.player-profile-identity,.player-profile-details,.player-profile-stats b,.player-profile-stats span',
  prematch: '.prematch-header,.prematch-team-logo,.prematch-team-name,.prematch-stat-row,.prematch-footer',
  intermission: '.intermission-header,.intermission-side-title,.intermission-event-row',
  lineups: '.lineups-header,.team-only-name,.starter-card:not(.empty)',
  top_scorers: '.scorer-prematch-header,.scorer-team-logo,.scorer-team-name,.scorer-player-name,.scorer-metrics > div',
  standings: '.stats-header,.standings-head,.standings-row',
  penalties: '.penalties-header,.penalties-home-row,.penalties-away-row',
};
interface MotionState {
  node: HTMLElement;
  kind: GraphicKind;
  visible: boolean;
  entered: boolean;
  generation: number;
  surface: HTMLElement;
  value: { alpha: number; y: number };
  animation?: gsap.core.Tween;
  details?: gsap.core.Timeline;
  cleanupDetails: () => void;
}
interface GoalState { key: string; phase: string; event: string; timeline: gsap.core.Timeline; cleanup: () => void }
interface GoalPose { target: Element; values: gsap.TweenVars }
const GOAL_PARTS: [string, string[]][] = [
  ['#bottom-goal-word', ['x', 'opacity', 'letterSpacing']],
  ['.goal-intro-rule', ['scaleX', 'opacity']],
  ['.studio-goal-echo', ['x', 'opacity']],
  ['.studio-goal-track', ['strokeDashoffset']],
  ['.studio-goal-chevron', ['x', 'opacity']],
  ['.studio-goal-beam', ['x', 'opacity']],
];
interface StatusState {
  token: symbol;
  tween: gsap.core.Tween;
  value: { alpha: number; x: number; height: number };
  exiting: boolean;
  done?: () => void;
}

/** Presentation-only engine. BroadcastFlow alone owns phase changes and durations. */
export class BroadcastMotion {
  private states = new Map<HTMLElement, MotionState>();
  private goals = new Map<HTMLElement, GoalState>();
  private statuses = new Map<HTMLElement, StatusState>();
  private reduced: () => boolean;
  private schedule: (callback: () => void) => unknown;

  constructor({ reduced = () => false, schedule = (fn: () => void) => requestAnimationFrame(fn) } = {}) {
    this.reduced = reduced;
    this.schedule = schedule;
  }
  private state(node: HTMLElement, kind: GraphicKind): MotionState {
    let state = this.states.get(node);
    if (!state) {
      state = { node, kind, visible: false, entered: false, generation: 0,
        surface: node.querySelector<HTMLElement>(SURFACES[kind] || ':scope') || node,
        value: { alpha: 1, y: 0 }, cleanupDetails: () => {} };
      this.states.set(node, state);
    }
    return state;
  }
  private paint(state: MotionState) {
    if (state.kind === 'scoreboard') state.surface.style.removeProperty('filter');
    else state.surface.style.filter = `opacity(${state.value.alpha})`;
    state.surface.style.translate = `0px ${state.value.y}px`;
  }
  private clearDetails(state: MotionState) {
    const timeline = state.details;
    state.details = undefined;
    timeline?.kill();
    state.cleanupDetails();
    state.cleanupDetails = () => {};
  }
  private scoreboardAboveViewport(state: MotionState) {
    // Include the clock and absolute powerplay queues, which can extend below
    // the scoreboard's own box. Rects include the Manager scale already.
    const boxes = [state.node, ...state.node.querySelectorAll('.scoreboard,.time-box,.sp-team-status-stack')]
      .map(node => node.getBoundingClientRect()).filter(rect => rect.height > 0);
    const fallback = 200 + Math.max(0, ...[...state.node.querySelectorAll('.sp-team-status-stack')]
      .map(stack => stack.children.length * 44));
    const bottom = boxes.length ? Math.max(...boxes.map(rect => rect.bottom)) - state.value.y : fallback;
    return -(Math.max(0, bottom) + 24);
  }
  private clearSurface(state: MotionState) {
    state.surface.style.removeProperty('filter');
    state.surface.style.removeProperty('translate');
    state.value = { alpha: 1, y: 0 };
  }
  setVisible(node: HTMLElement | null, visible: boolean, kind: GraphicKind) {
    if (!node) return;
    const state = this.state(node, kind);
    if (state.visible === visible && node.dataset.spMotion) return;
    const interrupted = state.animation?.isActive() || node.dataset.spMotion === 'exiting';
    const resumeDetails = visible && interrupted && state.details && state.details.totalProgress() < 1;
    state.animation?.kill();
    // Freeze any unfinished content during an outro. Resetting it here would
    // snap the names into place just as the bottom starts disappearing.
    if (!visible) state.details?.pause();
    else if (!resumeDetails) this.clearDetails(state);
    state.visible = visible;
    const generation = ++state.generation;
    if (this.reduced() || (!visible && !state.entered)) {
      state.entered = visible;
      node.dataset.spMotion = visible ? 'on' : 'off';
      this.clearDetails(state);
      this.clearSurface(state);
      return;
    }
    node.dataset.spMotion = visible ? 'on' : 'exiting';
    if (visible && !interrupted) {
      state.value = { alpha: kind === 'scoreboard' ? 1 : 0,
        y: kind === 'scoreboard' ? -Math.max(window.innerHeight, 320) : kind === 'bottom' || kind === 'profile' ? 8 : 10 };
      this.paint(state);
    }
    this.schedule(() => {
      if (generation !== state.generation) return;
      state.entered = visible || state.entered;
      if (visible && kind === 'scoreboard' && !interrupted) {
        // Measure after the state adapter has populated the current queues.
        state.value.y = this.scoreboardAboveViewport(state);
        this.paint(state);
      }
      const targetY = visible ? 0 : kind === 'scoreboard' ? this.scoreboardAboveViewport(state)
        : kind === 'bottom' || kind === 'profile' ? state.value.y : 5;
      state.animation = gsap.to(state.value, {
        alpha: kind === 'scoreboard' || visible ? 1 : 0, y: targetY,
        duration: kind === 'scoreboard' ? visible ? .64 : .42 : visible ? .86 : .4,
        // A decisive arrival with a long brake, then acceleration back upwards.
        // Keep the trajectory monotonic: no bounce or separate text movement.
        ease: kind === 'scoreboard' ? visible ? 'power3.out' : 'power2.in' : visible ? ENTER : EXIT,
        onUpdate: () => { if (generation === state.generation) this.paint(state); },
        onComplete: () => {
          if (generation !== state.generation) return;
          if (!visible) {
            state.entered = false; node.dataset.spMotion = 'off';
            this.clearDetails(state);
          }
          this.clearSurface(state);
        },
      });
      if (resumeDetails) state.details?.play();
      else if (visible && kind !== 'scoreboard' && !node.classList.contains('goal-intro')) this.revealDetails(node, kind);
    });
  }
  revealDetails(node: HTMLElement | null, kind: GraphicKind, selector?: string | null,
    { duration = 580, start = 100, stagger = 36, distance = 7 }: DetailOptions = {}) {
    if (!node || this.reduced() || kind === 'scoreboard') return;
    const state = this.state(node, kind);
    if (!state.visible) return;
    this.clearDetails(state);
    const elements = [...node.querySelectorAll<HTMLElement>(selector || DETAILS[kind] || ':not(*)')]
      .filter(el => !el.hidden).slice(0, 40);
    const connected = kind === 'bottom' || kind === 'profile';
    const step = connected ? Math.min(stagger, 14) : Math.min(stagger, 28);
    const travel = connected ? Math.min(distance, 3) : Math.min(distance, 5);
    const originals = elements.map(el => ({ el, filter: el.style.filter, translate: el.style.translate }));
    state.cleanupDetails = () => originals.forEach(({ el, filter, translate }) => {
      el.style.filter = filter; el.style.translate = translate;
    });
    const timeline = gsap.timeline({ paused: true, onComplete: () => {
      if (state.details === timeline && state.visible) state.cleanupDetails();
    } });
    elements.forEach((el, index) => {
      const value = { alpha: 0, y: travel };
      const paint = () => {
        if (state.details !== timeline || !state.visible) return;
        el.style.filter = `opacity(${value.alpha})`; el.style.translate = `0px ${value.y}px`;
      };
      el.style.filter = 'opacity(0)'; el.style.translate = `0px ${travel}px`;
      timeline.to(value, { alpha: 1, y: 0, duration: duration / 1000, ease: ENTER, onUpdate: paint },
        Math.max(0, start) / 1000 + Math.min(index, 9) * step / 1000);
    });
    state.details = timeline;
    timeline.play(Math.max(0, -start / 1000));
  }
  scoreChanged(node: HTMLElement | null, previous: unknown, next: unknown) {
    if (!node || previous == null || previous === next || this.reduced()) return;
    // Scores update in place as well: no fading or hopping of scoreboard text.
    if (node.closest('#scoreboard-wrapper')) return;
    const state = this.state(node, 'score');
    state.animation?.kill();
    state.value = { alpha: .35, y: 5 };
    this.paint(state);
    state.animation = gsap.to(state.value, { alpha: 1, y: 0, duration: .48, ease: ENTER,
      onUpdate: () => this.paint(state), onComplete: () => this.clearSurface(state) });
  }
  private status(node: HTMLElement, side: string, exiting: boolean, done?: () => void) {
    const previous = this.statuses.get(node);
    previous?.tween.kill();
    if (this.reduced()) { this.clearStatus(node); if (exiting) done?.(); return; }
    const height = node.scrollHeight || 44;
    const token = Symbol('status');
    const value = previous?.value || { alpha: exiting ? 1 : 0, x: exiting ? 0 : side === 'team2' ? 18 : -18, height };
    const paint = () => {
      node.style.filter = `opacity(${value.alpha})`;
      node.style.translate = `${value.x}px 0px`;
      if (exiting) { node.style.height = `${value.height}px`; node.style.maxHeight = `${value.height}px`; }
    };
    paint();
    const tween = gsap.to(value, { alpha: exiting ? 0 : 1, x: exiting ? side === 'team2' ? 14 : -14 : 0,
      height: exiting ? 0 : height, duration: exiting ? .34 : .62, ease: exiting ? EXIT : ENTER,
      onUpdate: () => { if (this.statuses.get(node)?.token === token) paint(); },
      onComplete: () => {
        if (this.statuses.get(node)?.token !== token) return;
        this.clearStatus(node); if (exiting) done?.();
      } });
    this.statuses.set(node, { token, tween, value, exiting, done });
  }
  private clearStatus(node: HTMLElement) {
    this.statuses.get(node)?.tween.kill();
    this.statuses.delete(node);
    for (const property of ['filter', 'translate', 'height', 'max-height']) node.style.removeProperty(property);
  }
  statusEnter(node: HTMLElement, side: string) { this.status(node, side, false); }
  statusExit(node: HTMLElement, side: string, done: () => void) { this.status(node, side, true, done); }
  cancelStatus(node: HTMLElement, side: string) { this.status(node, side, false); }
  private goalPose(node: HTMLElement): GoalPose[] {
    return GOAL_PARTS.flatMap(([selector, properties]) => [...node.querySelectorAll(selector)].map(target => ({
      target,
      values: Object.fromEntries(properties.map(property => [property, gsap.getProperty(target, property)])),
    })));
  }
  presentGoal(node: HTMLElement, phase: GoalPhase, visible: boolean) {
    const existing = this.goals.get(node);
    if (!visible) {
      // Freeze the curtain through the outro; never uncover the waiting scorer.
      existing?.timeline.pause();
      return;
    }
    const key = `${phase.key}:${this.reduced()}`;
    if (existing?.key === key) return;
    const event = phase.key.slice(0, phase.key.lastIndexOf(':'));
    // Capture the visible vector pose before reverting the previous context.
    // The next phase continues that pose instead of snapping its artwork home.
    const handoff = phase.reveal && existing?.phase === 'GOAL_INTRO' && existing.event === event && !this.reduced()
      ? this.goalPose(node) : [];
    existing?.timeline.kill();
    existing?.cleanup();
    this.goals.delete(node);
    const curtain = node.querySelector<HTMLElement>('.bottom-goal-intro');
    if (!curtain) return;
    const echo = node.querySelector<SVGElement>('.studio-goal-echo');
    if (echo) echo.textContent = node.querySelector('#bottom-goal-word')?.textContent || '';
    const scope = gsap.context(() => {}, node);
    let timeline!: gsap.core.Timeline;
    scope.add(() => {
      timeline = gsap.timeline({ paused: true });
      if (!phase.overlay) return;
      if (phase.reveal) {
        if (!this.reduced()) {
          gsap.set('.studio-goal-echo', { x: -28, opacity: .13 });
          gsap.set('.studio-goal-track', { strokeDashoffset: 0 });
          for (const pose of handoff) gsap.set(pose.target, pose.values);
        }
        // The reference geometry has an !important clip-path reset on drawers.
        // Animate a custom property inside the Studio mask so it wins that reset.
        timeline.fromTo(curtain, this.reduced() ? { '--studio-goal-opacity': 1 } : { '--studio-goal-cut': '0%' },
          { ...(this.reduced() ? { '--studio-goal-opacity': 0 } : { '--studio-goal-cut': '100%' }),
            duration: phase.duration, ease: ENTER }, 0);
        if (!this.reduced()) timeline.fromTo('.goal-intro-lockup', { x: 0, opacity: 1 },
          { x: -28, opacity: 0, duration: phase.duration, ease: ENTER }, 0);
      } else if (!this.reduced()) {
        timeline.fromTo('#bottom-goal-word', { x: 56, opacity: 0, letterSpacing: '.2em' },
          { x: 0, opacity: 1, letterSpacing: '.12em', duration: .92, ease: ENTER }, .06);
        timeline.fromTo('.goal-intro-rule', { scaleX: 0, opacity: 0 },
          { scaleX: 1, opacity: .65, duration: .82, stagger: .04, ease: ENTER }, .16);
        timeline.fromTo('.studio-goal-echo', { x: 62, opacity: 0 },
          { x: -28, opacity: .13, duration: 2, ease: ENTER }, .08);
        timeline.fromTo('.studio-goal-track', { strokeDashoffset: 1400 },
          { strokeDashoffset: 0, duration: 1.2, stagger: .1, ease: 'power3.inOut' }, .05);
        timeline.fromTo('.studio-goal-chevron', { x: 42, opacity: 0 },
          { x: 0, opacity: .3, duration: .94, stagger: .04, ease: ENTER }, .1);
        timeline.fromTo('.studio-goal-beam', { x: 1300, opacity: 0 },
          { x: -350, opacity: .5, duration: 1.5, ease: ENTER }, .32);
        timeline.to('.studio-goal-beam', { opacity: 0, duration: .25 }, 1.55);
      }
    });
    this.goals.set(node, { key, phase: phase.phase, event, timeline, cleanup: () => scope.revert() });
    // Seek the existing server phase, including refreshes and late OBS frames.
    if (phase.overlay) timeline.play(Math.min(phase.elapsed, timeline.duration()));
  }
  settle() {
    for (const [node, status] of this.statuses) {
      this.clearStatus(node);
      if (status.exiting) status.done?.();
    }
    for (const state of this.states.values()) {
      ++state.generation;
      state.animation?.kill(); this.clearDetails(state);
      this.clearSurface(state);
      if (state.kind !== 'score') {
        state.entered = state.visible;
        state.node.dataset.spMotion = state.visible ? 'on' : 'off';
      }
    }
    for (const [node, goal] of this.goals) {
      goal.timeline.kill(); goal.cleanup();
      // Force reconstruction on the next state read after preference changes.
      this.goals.delete(node);
    }
  }
}
