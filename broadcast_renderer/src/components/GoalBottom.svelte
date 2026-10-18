<script lang="ts">
  import GoalArtwork from './GoalArtwork.svelte';
</script>
<!-- Goal bottom bar -->
<div class="bottom-bar studio-lower-third" id="bottom-bar">
  <div class="bottom-team-block" id="bottom-team-block">
    <span class="bottom-team-accent" aria-hidden="true"></span>
    <img id="bottom-team-logo" src={undefined} alt="Team logo" />
  </div>
  <div class="bottom-match-state" aria-label="Estado actual del partido">
    <div class="bottom-match-time" id="bottom-match-time">00:00</div>
    <div class="bottom-current-score" id="bottom-current-score">0–0</div>
  </div>
  <div class="bottom-goal-intro" id="bottom-goal-intro" data-word="GOL" aria-hidden="true">
    <GoalArtwork />
    <div class="goal-intro-lockup"><span class="goal-intro-rule"></span><span id="bottom-goal-word">GOL</span><span class="goal-intro-rule"></span></div>
  </div>
  <div class="bottom-event-copy">
    <div class="bottom-person-row bottom-scorer-row">
      <span class="bottom-person-number" id="bottom-scorer-number"></span>
      <span class="bottom-person-name" id="bottom-scorer-name"></span>
      <span class="bottom-goal-count" id="bottom-goal-count"></span>
    </div>
    <div class="bottom-person-row bottom-assistant-row" id="bottom-assistant-row" hidden>
      <span class="bottom-person-number" id="bottom-assistant-number"></span>
      <span class="bottom-person-name" id="bottom-assistant-name"></span>
    </div>
  </div>
</div>
