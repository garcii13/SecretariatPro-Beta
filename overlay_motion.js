/* Presentation only: no score, clock, replay or broadcast state is changed here. */
(function (root, factory) {
  const Motion = factory();
  if (typeof module === "object" && module.exports) module.exports = Motion;
  else root.SPBroadcastMotion = Motion;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  const ENTER = "cubic-bezier(.16,1,.3,1)";
  const EXIT = "cubic-bezier(.4,0,.8,.2)";
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
    constructor({reduced = () => false, schedule = fn => requestAnimationFrame(fn)} = {}) {
      this.reduced = reduced;
      this.schedule = schedule;
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
      state.visible = visible;
      const generation = ++state.generation;
      this._cancel(state.animations);
      this._cancel(state.details);
      node.dataset.spMotion = visible ? "on" : "off";
      if (this.reduced() || typeof node.animate !== "function") return;
      if (!visible && !state.entered) return;
      state.entered = true;
      node.dataset.spMotion = visible ? "on" : "exiting";
      this.schedule(() => {
        if (generation !== state.generation) return;
        const surface = SURFACES[kind] ? node.querySelector(SURFACES[kind]) || node : node;
        const vertical = kind === "scoreboard" ? -18 : kind === "bottom" || kind === "profile" ? 26 : 22;
        // Legacy visibility rules use !important opacity. An opacity filter
        // fades the surface without changing those state rules or its geometry.
        const animation = this._play(surface, visible ? [
          {filter: "opacity(0)", translate: `0px ${vertical}px`},
          {filter: "opacity(1)", translate: "0px 0px"},
        ] : [
          {filter: "opacity(1)", translate: "0px 0px"},
          {filter: "opacity(0)", translate: `0px ${kind === "scoreboard" ? -10 : 12}px`},
        ], {duration: visible ? 640 : 220, easing: visible ? ENTER : EXIT}, state.animations);
        if (visible && !node.classList.contains("goal-intro")) this.revealDetails(node, kind);
        if (!visible) {
          const complete = () => {
            if (generation !== state.generation) return;
            node.dataset.spMotion = "off";
          };
          if (animation) animation.finished.then(complete, complete);
          else complete();
        }
      });
    }
    revealDetails(node, kind, selector = null) {
      if (!node || this.reduced()) return;
      const state = this._state(node, kind);
      if (!state.visible) return;
      this._cancel(state.details);
      const selectors = selector ? [selector] : DETAILS[kind] || [];
      const elements = selectors.flatMap(value => [...node.querySelectorAll(value)]).filter(el => !el.hidden).slice(0, 32);
      elements.forEach((el, index) => {
        const horizontal = kind === "scoreboard" && (el.classList.contains("team1-name-box") || el.closest(".team1-bar")) ? -16
          : kind === "scoreboard" && (el.classList.contains("team2-name-box") || el.closest(".team2-bar")) ? 16 : 0;
        this._play(el, [
          {opacity: 0, translate: `${horizontal}px ${horizontal ? 0 : 9}px`},
          {opacity: 1, translate: "0px 0px"},
        ], {duration: 480, delay: 80 + Math.min(index, 7) * 38, easing: ENTER}, state.details);
      });
    }
    scoreChanged(node, previous, next) {
      if (!node || previous == null || previous === next || this.reduced()) return;
      const state = this._state(node, "score");
      this._cancel(state.animations);
      this._play(node, [
        {opacity: .4, translate: "0px 7px"},
        {opacity: 1, translate: "0px 0px"},
      ], {duration: 340, easing: ENTER}, state.animations);
    }
    settle() {
      for (const state of this.states.values()) {
        state.generation += 1;
        this._cancel(state.animations);
        this._cancel(state.details);
        if (state.kind !== "score") state.node.dataset.spMotion = state.visible ? "on" : "off";
      }
    }
  }
  return BroadcastMotion;
});
