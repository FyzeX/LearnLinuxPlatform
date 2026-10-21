/* Трекер прогресса: ежедневная цель по минутам + задачи (todo), всё в SQLite. */

(function () {
  const listEl = document.getElementById('tasksList');
  const formEl = document.getElementById('taskForm');
  if (!listEl || !formEl) return;

  const minEl = document.getElementById('todayMinutes');
  const fillEl = document.getElementById('todayFill');
  const pctEl = document.getElementById('goalPct');
  const goalSel = document.getElementById('dailyGoal');

  // ----- цель дня -----
  let goal = parseInt(localStorage.getItem('dailyGoal') || '25', 10);
  goalSel.value = String(goal);
  goalSel.addEventListener('change', () => {
    goal = parseInt(goalSel.value, 10);
    localStorage.setItem('dailyGoal', goal);
    updateGoal();
  });

  let todayMinutes = 0;

  function updateGoal() {
    const pct = Math.min(100, Math.round(todayMinutes * 100 / goal));
    minEl.textContent = todayMinutes;
    fillEl.style.width = pct + '%';
    pctEl.textContent = pct >= 100 ? 'цель выполнена 🎉' : pct + '%';
  }

  function setTodayFromDashboard(data) {
    const t = new Date().toISOString().slice(0, 10);
    const rec = data.heatmap[t] || {minutes: 0, lessons: 0};
    todayMinutes = rec.minutes;
    updateGoal();
  }

  window.onHeatmapLoaded = setTodayFromDashboard;   // heatmap.js вызовет после загрузки
  window.addEventListener('pomodoro:done', () => {
    // перезапросим данные через heatmap-обновление
    window.refreshHeatmap && window.refreshHeatmap();
  });

  // ----- задачи -----
  function esc(s) { return String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }

  async function loadTasks() {
    const r = await fetch('/api/tasks');
    render(await r.json());
  }
  function render(tasks) {
    listEl.innerHTML = tasks.map(t =>
      `<li class="${t.done ? 'done' : ''}" data-id="${t.id}">
         <input type="checkbox" class="t-chk" ${t.done ? 'checked' : ''} id="tk${t.id}" hidden>
         <label class="check" for="tk${t.id}"><span class="box"></span></label>
         <span class="t">${esc(t.title)}</span>
         <button class="del" title="Удалить">✕</button>
       </li>`).join('') || '<li class="muted" style="border:0">Задач пока нет — добавьте первую 👇</li>';
  }

  formEl.addEventListener('submit', async e => {
    e.preventDefault();
    const inp = document.getElementById('taskInput');
    const title = inp.value.trim();
    if (!title) return;
    await fetch('/api/tasks', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({title})
    });
    inp.value = '';
    loadTasks();
  });

  listEl.addEventListener('click', async e => {
    const li = e.target.closest('li[data-id]');
    if (!li) return;
    const id = li.dataset.id;
    if (e.target.closest('.del')) {
      await fetch('/api/tasks/' + id, {method: 'DELETE'});
      loadTasks();
    } else if (e.target.closest('.check') || e.target.classList.contains('t')) {
      const r = await fetch(`/api/tasks/${id}/toggle`, {method: 'POST'});
      const d = await r.json();
      li.classList.toggle('done', !!d.done);
      const chk = li.querySelector('.t-chk');
      if (chk) chk.checked = !!d.done;
    }
  });

  loadTasks();
})();
