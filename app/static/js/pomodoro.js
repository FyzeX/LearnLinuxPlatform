/* Помидоро-таймер: фокус 25 / перерывы 5 и 15, кольцо прогресса,
   учёт помидоро (4 -> длинный перерыв), сохранение сессий на сервер. */

(function () {
  const card = document.getElementById('pomodoroCard');
  if (!card) return;

  const CIRC = 2 * Math.PI * 52;
  const ring = card.querySelector('#ringFg');
  const timeEl = card.querySelector('#pomoTime');
  const btnStart = card.querySelector('#pomoStart');
  const btnPause = card.querySelector('#pomoPause');
  const btnReset = card.querySelector('#pomoReset');
  const dotsEl = card.querySelector('#pomoDots');
  const modesEl = card.querySelector('#pomoModes');
  const sessionCounter = card.querySelector('.card-head .muted');

  ring.style.strokeDasharray = CIRC;

  let mode = 'focus';
  let totalSec = 25 * 60;
  let left = totalSec;
  let running = false;
  let tickId = null;
  let pomodoros = parseInt(localStorage.getItem('pomoCount') || '0', 10);

  function fmt(s) {
    const m = Math.floor(s / 60), ss = s % 60;
    return String(m).padStart(2, '0') + ':' + String(ss).padStart(2, '0');
  }
  function render() {
    timeEl.textContent = fmt(left);
    ring.style.strokeDashoffset = CIRC * (1 - left / totalSec);
    ring.style.stroke = mode === 'focus' ? 'var(--red)' : 'var(--green)';
    document.title = (running ? (mode === 'focus' ? '🍅 ' : '☕ ') : '') +
      fmt(left) + (running ? ' · LinuxDevOps' : '');
    dotsEl.innerHTML = [0,1,2,3].map(i =>
      `<i class="${i < (pomodoros % 4) ? 'filled' : ''}"></i>`).join('');
  }
  function setMode(m, min) {
    mode = m; totalSec = min * 60; left = totalSec; stop();
    modesEl.querySelectorAll('.seg-btn').forEach(b =>
      b.classList.toggle('active', b.dataset.mode === m));
    render();
  }
  function start() {
    if (running) return;
    running = true;
    btnStart.disabled = true; btnPause.disabled = false;
    tickId = setInterval(() => {
      left--;
      if (left <= 0) finish();
      else if (left % 5 === 0) saveState();
      render();
    }, 1000);
    saveState();
  }
  function stop() {
    running = false;
    clearInterval(tickId);
    btnStart.disabled = false; btnPause.disabled = true;
    btnStart.textContent = left < totalSec ? 'Продолжить' : 'Старт';
  }
  function beep() {
    try {
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const o = ctx.createOscillator(), g = ctx.createGain();
      o.connect(g); g.connect(ctx.destination);
      o.frequency.value = 880; g.gain.setValueAtTime(.15, ctx.currentTime);
      o.start(); o.stop(ctx.currentTime + .6);
    } catch (e) {}
  }
  function finish() {
    stop();
    beep();
    if (mode === 'focus') {
      pomodoros++;
      localStorage.setItem('pomoCount', pomodoros);
      const label = document.querySelector('.user-chip')?.textContent || '';
      fetch('/api/pomodoro/complete', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({minutes: Math.round(totalSec / 60), mode: 'focus', label})
      }).then(r => r.json()).then(d => {
        if (sessionCounter && d.stats) sessionCounter.textContent = `${d.stats.sessions} сессий всего`;
        window.dispatchEvent(new CustomEvent('pomodoro:done', {detail: d.stats}));
      }).catch(() => {});
      toast('🍅 Помидоро завершён! Время перерыва.');
      setMode(pomodoros % 4 === 0 ? 'long' : 'short',
              pomodoros % 4 === 0 ? 15 : 5);
      return;
    }
    toast('☕ Перерыв окончен — возвращаемся к-focus!'.replace('-focus', ' фокусу'));
    setMode('focus', 25);
  }
  function saveState() {
    localStorage.setItem('pomoState', JSON.stringify({mode, left, totalSec}));
  }

  btnStart.addEventListener('click', start);
  btnPause.addEventListener('click', stop);
  btnReset.addEventListener('click', () => { stop(); left = totalSec; btnStart.textContent = 'Старт'; render(); });
  modesEl.addEventListener('click', e => {
    const b = e.target.closest('.seg-btn');
    if (b) setMode(b.dataset.mode, parseInt(b.dataset.min, 10));
  });

  // восстановление после перезагрузки страницы (без автостарта)
  try {
    const st = JSON.parse(localStorage.getItem('pomoState') || 'null');
    if (st && st.left > 0) { mode = st.mode; totalSec = st.totalSec; left = st.left; }
  } catch (e) {}
  render();
})();
