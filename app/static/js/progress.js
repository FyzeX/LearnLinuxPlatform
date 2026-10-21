/* Отметка уроков пройденными (трек и страница урока) + обновление прогресс-баров. */

(function () {
  const boxes = document.querySelectorAll('.lesson-toggle');
  if (!boxes.length) return;

  boxes.forEach(cb => cb.addEventListener('change', async () => {
    const r = await fetch('/api/toggle-lesson', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({slug: cb.dataset.slug})
    });
    if (!r.ok) { window.toast && toast('Не удалось сохранить прогресс'); return; }
    const d = await r.json();
    const row = cb.closest('.lesson-row');
    if (row) row.classList.toggle('done', d.completed);
    window.dispatchEvent(new CustomEvent('progress:changed', {detail: d.stats}));
    window.toast && toast(d.completed ? '✅ Урок отмечен как пройденный' : '↩️ Отметка снята');
  }));

  // пересчёт полоски прогресса на странице трека
  window.addEventListener('progress:changed', stats => {
    const s = stats.detail;
    const bar = document.querySelector('.track-hero .progress-fill');
    if (bar && s.lessons_total) {
      const doneInTrack = document.querySelectorAll('.lesson-row.done').length;
      const totalInTrack = document.querySelectorAll('.lesson-row').length;
      bar.style.width = Math.round(doneInTrack * 100 / (totalInTrack || 1)) + '%';
      const meta = document.querySelector('.track-hero p');
      if (meta) meta.textContent = `${totalInTrack} уроков · пройдено ${doneInTrack}`;
    }
  });
})();
