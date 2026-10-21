/* Дашборд: статистика + прогресс по трекам (данные из /api/dashboard, общий с heatmap.js). */

(function () {
  const el = document.getElementById('trackProgress');
  if (!el) return;

  function paint(data) {
    const s = data.stats;
    document.getElementById('stLessons').textContent = `${s.lessons_done}/${s.lessons_total}`;
    document.getElementById('stMinutes').textContent = s.minutes;
    document.getElementById('stSessions').textContent = s.sessions;
    document.getElementById('stStreak').textContent = s.streak;

    el.innerHTML = data.tracks.map(t => {
      const pct = Math.round(t.done * 100 / (t.total || 1));
      return `<div class="tp-row">
        <a href="/tracks/${t.key}">${t.icon} ${t.name}</a>
        <div class="progress-bar sm"><div class="progress-fill" style="width:${pct}%;background:${t.color}"></div></div>
        <span class="muted">${t.done}/${t.total}</span>
      </div>`;
    }).join('');
  }

  window.onHeatmapLoaded = paint;   // heatmap.js уже грузит /api/dashboard
  // если heatmap ещё не успел — подстрахуемся
  fetch('/api/dashboard').then(r => r.json()).then(paint).catch(() => {});
  window.addEventListener('progress:changed', () => {
    fetch('/api/dashboard').then(r => r.json()).then(d => { paint(d); window.refreshHeatmap && window.refreshHeatmap(); });
  });
})();
