<!-- ---------- SCOREBOARD ---------- -->
<div class="scoreboard-wrapper hidden" id="scoreboard-wrapper">
  <div class="scoreboard" id="scoreboard">
    <div class="section team1-bar">
      <img id="team1-logo" src={undefined} alt="Team 1 Logo" />
    </div>

    <div class="section grey team1-name-box">
      <input type="text" class="score-input team1-name" placeholder="Team 1" readonly tabindex="-1" />
    </div>

    <div class="section center">
      <input type="text" class="score-box team1-score" placeholder="0" readonly tabindex="-1" />
      <div class="logo-liga">
        <img id="scoreboard-league-logo" src={undefined} alt="League Logo" class="league-logo" />
      </div>
      <input type="text" class="score-box team2-score" placeholder="0" readonly tabindex="-1" />
      <div class="time-box"><span class="clock-content"><span id="clock-period" hidden></span><span id="match-time">00:00</span></span>
        <div id="period-strip" class="period-strip hidden" aria-label="Periodo actual"></div>
      </div>
    </div>

    <div class="section grey team2-name-box">
      <input type="text" class="score-input team2-name" placeholder="Team 2" readonly tabindex="-1" />
    </div>

    <div class="section team2-bar">
      <img id="team2-logo" src={undefined} alt="Team 2 Logo" />
    </div>

    <div class="sp-team-status-stack sp-team-status-stack--home" id="team1-status-stack" aria-live="polite" aria-label="Estados del equipo local"></div>
    <div class="sp-team-status-stack sp-team-status-stack--away" id="team2-status-stack" aria-live="polite" aria-label="Estados del equipo visitante"></div>
  </div>
</div>
