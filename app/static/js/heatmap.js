/* GitHub-style contribution heatmap: столбцы — недели, строки — дни (пн..вс). */

(function () {
  const wrap = document.getElementById('heatmap');
  if (!wrap) return;

  const DAY_MS = 86400000;
  let cache = null;      // {stats, heatmap, today}
  let weeksShown = parseInt(
    (document.querySelector('#heatmapRange .seg-btn.active') || {dataset: {}}).dataset.weeks || 26, 10);

  const MONTHS_RU = ['янв','фев','мар','апр','май','июн','июл','авг','сен','окт','ноя','дек'];
  const DOW = ['', 'пн', '', 'ср', '', 'пт', ''];

  function level(v) {
    if (!v) return 0;
    if (v <= 20) return 1;
    if (v <= 45) return 2;
    if (v <= 90) return 3;
    return 4;
  }
  function iso(d) {
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') +
           '-' + String(d.getDate()).padStart(2, '0');
  }

  async function load() {
    const r = await fetch('/api/dashboard?weeks=53');
    cache = await r.json();
    draw();
    window.onHeatmapLoaded && window.onHeatmapLoaded(cache);
  }

  function draw() {
    const today = new Date(cache.today + 'T00:00:00');
    const data = cache.heatmap;
    const dayIdx = (today.getDay() + 6) % 7;            // пн=0 ... вс=6
    const weekEnd = new Date(today.getTime() + (6 - dayIdx) * DAY_MS);

    // колонки недель (старые -> новые)
    const cols = [];
    for (let w = weeksShown - 1; w >= 0; w--) {
      const start = new Date(weekEnd.getTime() - (w * 7 + (6 - dayIdx)) * DAY_MS);
      const days = [];
      for (let d = 0; d < 7; d++) days.push(new Date(start.getTime() + d * DAY_MS));
      cols.push(days);
    }

    // подписи месяцев
    const monthLabels = [];
    let prevM = -1;
    cols.forEach((days, wi) => {
      const m = days[0].getMonth();
      if (m !== prevM) { monthLabels.push({wi, m}); prevM = m; }
    });
    let mlHtml = '<div class="hm-months" style="position:relative;height:16px;margin-left:22px">';
    monthLabels.forEach(({wi, m}, i) => {
      if (i === 0) return;
      mlHtml += `<span style="position:absolute;left:${wi * 16}px;min-width:auto">${MONTHS_RU[m]}</span>`;
    });
    mlHtml += '</div>';

    let totalLessons = 0, totalMinutes = 0;
    let gridHtml = '<div class="hm-grid"><div class="hm-days">' +
      DOW.map(x => `<b>${x}</b>`).join('') + '</div>';

    cols.forEach(days => {
      let col = '<div class="hm-col">';
      days.forEach(dt => {
        const key = iso(dt);
        const rec = data[key] || {lessons: 0, minutes: 0};
        const val = rec.lessons * 10 + rec.minutes;
        const lv = level(val);
        const future = dt > today;
        if (!future) { totalLessons += rec.lessons; totalMinutes += rec.minutes; }
        const tip = future ? '' :
          `${rec.lessons} урок(ов) · ${rec.minutes} мин — ${dt.getDate()} ${MONTHS_RU[dt.getMonth()]} ${dt.getFullYear()}`;
        col += `<div class="hm-cell lv-${lv}"${tip ? ` data-tip="${tip.replace(/"/g, '&quot;')}"` : ''}></div>`;
      });
      gridHtml += col + '</div>';
    });
    gridHtml += '</div>';

    wrap.innerHTML = mlHtml + gridHtml;

    const tEl = document.getElementById('heatTotal');
    const mEl = document.getElementById('heatMinutes');
    if (tEl) tEl.textContent = totalLessons;
    if (mEl) mEl.textContent = totalMinutes;

    let tipEl = null;
    wrap.addEventListener('mousemove', e => {
      const cell = e.target.closest('.hm-cell');
      if (!cell || !cell.dataset.tip) {
        if (tipEl) { tipEl.remove(); tipEl = null; }
        return;
      }
      if (!tipEl) { tipEl = document.createElement('div'); tipEl.className = 'hm-tooltip'; document.body.appendChild(tipEl); }
      tipEl.textContent = cell.dataset.tip;
      tipEl.style.left = Math.min(e.clientX + 12, innerWidth - 220) + 'px';
      tipEl.style.top = (e.clientY - 40) + 'px';
    });
    wrap.addEventListener('mouseleave', () => { if (tipEl) { tipEl.remove(); tipEl = null; } });
  }

  const rangeCtl = document.getElementById('heatmapRange');
  if (rangeCtl) rangeCtl.addEventListener('click', e => {
    const b = e.target.closest('.seg-btn');
    if (!b) return;
    rangeCtl.querySelectorAll('.seg-btn').forEach(x => x.classList.toggle('active', x === b));
    weeksShown = parseInt(b.dataset.weeks, 10);
    draw();
  });

  window.refreshHeatmap = function () { if (cache) load(); };
  load();
})();
