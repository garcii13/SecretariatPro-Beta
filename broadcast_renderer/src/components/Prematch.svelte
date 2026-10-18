<!-- ---------- PREMATCH MODAL ---------- -->
<div id="prematch-modal" class="modal hidden">
  <div class="prematch-panel">
    <div class="prematch-accent prematch-accent-home" id="prematch-team1-stripe"></div>
    <div class="prematch-accent prematch-accent-away" id="prematch-team2-stripe"></div>

    <header class="prematch-header">
      <div class="prematch-header-copy">
        <div class="prematch-kicker">PREMATCH</div>
        <div class="league-name" id="prematch-league-name">Liga Oro</div>
      </div>
    </header>

    <div class="prematch-main">
      <section class="prematch-team-card prematch-team-home" id="prematch-team1-card">
        <div class="prematch-team-glow" id="prematch-team1-glow"></div>
        <img id="prematch-team1-logo" class="prematch-team-logo" src={undefined} alt="Team 1 Logo" />
        <div id="prematch-team1-name" class="prematch-team-name">El Valle</div>
        <div class="prematch-team-role">LOCAL</div>
      </section>

      <section class="prematch-comparison">
        <div class="prematch-stat-row prematch-stat-featured">
          <div class="prematch-stat-value" id="prematch-team1-position">1º</div>
          <div class="prematch-stat-label">POSICIÓN</div>
          <div class="prematch-stat-value" id="prematch-team2-position">2º</div>
        </div>
        <div class="prematch-stat-row">
          <div class="prematch-stat-value" id="prematch-team1-points">42</div>
          <div class="prematch-stat-label">PUNTOS</div>
          <div class="prematch-stat-value" id="prematch-team2-points">39</div>
        </div>
        <div class="prematch-stat-row">
          <div class="prematch-stat-value prematch-stat-record" id="prematch-team1-wins">14</div>
          <div class="prematch-stat-label">V · E · D</div>
          <div class="prematch-stat-value prematch-stat-record" id="prematch-team2-wins">13</div>
        </div>
        <div class="prematch-stat-row">
          <div class="prematch-stat-value" id="prematch-team1-goals-for">60</div>
          <div class="prematch-stat-label">GOLES A FAVOR</div>
          <div class="prematch-stat-value" id="prematch-team2-goals-for">58</div>
        </div>
        <div class="prematch-stat-row">
          <div class="prematch-stat-value" id="prematch-team1-goals-against">25</div>
          <div class="prematch-stat-label">GOLES EN CONTRA</div>
          <div class="prematch-stat-value" id="prematch-team2-goals-against">30</div>
        </div>
      </section>

      <section class="prematch-team-card prematch-team-away" id="prematch-team2-card">
        <div class="prematch-team-glow" id="prematch-team2-glow"></div>
        <img id="prematch-team2-logo" class="prematch-team-logo" src={undefined} alt="Team 2 Logo" />
        <div id="prematch-team2-name" class="prematch-team-name">Leganés</div>
        <div class="prematch-team-role">VISITANTE</div>
      </section>
    </div>

    <footer class="prematch-footer prematch-footer-split">
      <div class="prematch-info-box prematch-info-venue">
        <span class="prematch-info-label">PABELLÓN</span>
        <span id="prematch-venue" class="prematch-info-value">—</span>
      </div>
      <img id="prematch-league-logo" class="prematch-league-logo prematch-footer-logo" src={undefined} alt="Competition logo" />
      <div class="prematch-info-box prematch-info-time">
        <span class="prematch-info-label">INICIO</span>
        <span id="prematch-kickoff" class="prematch-info-value">19:30h</span>
      </div>
    </footer>
  </div>
</div>
