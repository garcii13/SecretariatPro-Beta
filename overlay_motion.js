/* Presentation only: no score, clock, replay or broadcast state is changed here. */
(function (root, factory) {
  const Motion = factory();
  if (typeof module === "object" && module.exports) module.exports = Motion;
  else root.SPBroadcastMotion = Motion;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  const ENTER = "cubic-bezier(.22,.68,.24,1)";
  const EXIT = "cubic-bezier(.4,0,.2,1)";
  const DETAILS = {
    scoreboard: [".center", ".team1-name-box", ".team2-name-box", ".team1-bar img", ".team2-bar img", ".clock-content"],
    bottom: [".bottom-match-state", ".bottom-scorer-row", ".bottom-assistant-row"],
    profile: [".player-profile-team-block img", ".player-profile-identity", ".player-profile-details", ".player-profile-stats > div"],
    prematch: [".prematch-header", ".prematch-team-logo", ".prematch-team-name", ".prematch-stat-row", ".prematch-footer"],
    intermission: [".intermission-header", ".intermission-side-title", ".intermission-event-row"],
    lineups: [".lineups-header", ".team-only-name", ".starter-card:not(.empty)"],
    top_scorers: [".scorer-prematch-header", ".scorer-team-logo", ".scorer-team-name", ".scorer-player-name", ".scorer-metrics > div"],
    standings: [".stats-header", ".standings-head", ".standings-row"],
    penalties: [".penalties-header", ".penalties-home-row", ".penalties-away-row"],
  };
  const SURFACES = {
    scoreboard: ".scoreboard", prematch: ".prematch-panel", lineups: ".lineups-panel",
    top_scorers: ".stats-panel", standings: ".stats-panel", penalties: ".penalties-panel",
  };

  class BroadcastMotion {
    constructor({reduced = () => false, schedule = fn => requestAnimationFrame(fn), sample = node => {
      if (typeof getComputedStyle !== "function") return null;
      const style = getComputedStyle(node);
      return {filter: style.filter === "none" ? "opacity(1)" : style.filter, translate: style.translate === "none" ? "0px 0px" : style.translate};
    }} = {}) {
      this.reduced = reduced;
      this.schedule = schedule;
      this.sample = sample;
      this.states = new Map();
    }
    _state(node, kind) {
      if (!this.states.has(node)) this.states.set(node, {node, kind, visible: false, generation: 0, animations: new Set(), details: new Set()});
      return this.states.get(node);
    }
    _cancel(animations) {
      for (const animation of animations) animation.cancel();
      animations.clear();
    }
    _play(node, frames, options, animations) {
      if (!node || typeof node.animate !== "function" || this.reduced()) return null;
      const animation = node.animate(frames, {...options, fill: "backwards"});
      animations.add(animation);
      animation.finished.then(() => animations.delete(animation), () => animations.delete(animation));
      return animation;
    }
    setVisible(node, visible, kind) {
      if (!node) return;
      const state = this._state(node, kind);
      if (state.visible === visible && node.dataset.spMotion) return;
      const surface = SURFACES[kind] ? node.querySelector(SURFACES[kind]) || node : node;
      const current = state.animations.size ? this.sample(surface) : null;
      state.visible = visible;
      const generation = ++state.generation;
      this._cancel(state.animations);
      this._cancel(state.details);
      node.dataset.spMotion = visible ? "on" : "off";
      if (this.reduced() || typeof node.animate !== "function") return;
      if (!visible && !state.entered) return;
      node.dataset.spMotion = visible ? "on" : "exiting";
      this.schedule(() => {
        if (generation !== state.generation) return;
        if (visible) state.entered = true;
        const vertical = kind === "scoreboard" ? -12 : kind === "bottom" || kind === "profile" ? 18 : 16;
        // Legacy visibility rules use !important opacity. An opacity filter
        // fades the surface without changing those state rules or its geometry.
        const animation = this._play(surface, visible ? [
          current || {filter: "opacity(0)", translate: `0px ${vertical}px`},
          {filter: "opacity(1)", translate: "0px 0px"},
        ] : [
          current || {filter: "opacity(1)", translate: "0px 0px"},
          {filter: "opacity(0)", translate: `0px ${kind === "scoreboard" ? -7 : 8}px`},
        ], {duration: visible ? 760 : 320, easing: visible ? ENTER : EXIT}, state.animations);
        if (visible && !node.classList.contains("goal-intro")) this.revealDetails(node, kind);
        if (!visible) {
          const complete = () => {
            if (generation !== state.generation) return;
            state.entered = false;
            node.dataset.spMotion = "off";
          };
          if (animation) animation.finished.then(complete, complete);
          else complete();
        }
      });
    }
    revealDetails(node, kind, selector = null, {duration = 540, start = 100, stagger = 32, distance = 6} = {}) {
      if (!node || this.reduced()) return;
      const state = this._state(node, kind);
      if (!state.visible) return;
      this._cancel(state.details);
      const selectors = selector ? [selector] : DETAILS[kind] || [];
      const elements = selectors.flatMap(value => [...node.querySelectorAll(value)]).filter(el => !el.hidden).slice(0, 32);
      elements.forEach((el, index) => {
        const horizontal = kind === "scoreboard" && (el.classList.contains("team1-name-box") || el.closest(".team1-bar")) ? -10
          : kind === "scoreboard" && (el.classList.contains("team2-name-box") || el.closest(".team2-bar")) ? 10 : 0;
        this._play(el, [
          {opacity: 0, translate: `${horizontal}px ${horizontal ? 0 : distance}px`},
          {opacity: 1, translate: "0px 0px"},
        ], {duration, delay: start + Math.min(index, 7) * stagger, easing: ENTER}, state.details);
      });
    }
    scoreChanged(node, previous, next) {
      if (!node || previous == null || previous === next || this.reduced()) return;
      const state = this._state(node, "score");
      this._cancel(state.animations);
      this._play(node, [
        {opacity: .4, translate: "0px 4px"},
        {opacity: 1, translate: "0px 0px"},
      ], {duration: 420, easing: ENTER}, state.animations);
    }
    settle() {
      for (const state of this.states.values()) {
        state.generation += 1;
        this._cancel(state.animations);
        this._cancel(state.details);
        if (state.kind !== "score") {
          state.entered = state.visible;
          state.node.dataset.spMotion = state.visible ? "on" : "off";
        }
      }
    }
  }
  return BroadcastMotion;
});
