<!-- ---------- INTERMISSION MODAL ---------- -->
<div class="intermission-modal" id="intermission-modal">
  <div class="intermission-content">
    <div class="intermission-header">
      <div class="intermission-team-summary intermission-home">
        <div class="team-stripe" id="intermission-team1-stripe"></div>
        <img src={undefined} alt="Team 1 Logo" class="team-logo" id="intermission-team1-logo" />
        <div class="team-name" id="intermission-team1-name">Team 1</div>
        <div class="team-score" id="intermission-team1-score">0</div>
      </div>
      <div class="intermission-center">
        <div class="league-logo-container">
          <img id="intermission-league-logo" src={undefined} alt="League Logo" class="league-logo" />
        </div>
        <div class="intermission-events-title">EVENTOS</div>
      </div>
      <div class="intermission-team-summary intermission-away">
        <div class="team-stripe" id="intermission-team2-stripe"></div>
        <div class="team-score" id="intermission-team2-score">0</div>
        <div class="team-name" id="intermission-team2-name">Team 2</div>
        <img src={undefined} alt="Team 2 Logo" class="team-logo" id="intermission-team2-logo" />
      </div>
    </div>
    <div class="intermission-events-columns">
      <div class="intermission-events-side intermission-events-home">
        <div class="intermission-side-title" id="intermission-events-home-title">LOCAL</div>
        <div class="intermission-events-viewport" id="intermission-events-home-viewport">
          <div class="intermission-events-list" id="intermission-events-home-list"></div>
        </div>
      </div>
      <div class="intermission-events-side intermission-events-away">
        <div class="intermission-side-title" id="intermission-events-away-title">VISITANTE</div>
        <div class="intermission-events-viewport" id="intermission-events-away-viewport">
          <div class="intermission-events-list" id="intermission-events-away-list"></div>
        </div>
      </div>
    </div>
  </div>
</div>
