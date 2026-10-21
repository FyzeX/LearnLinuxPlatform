/* Общая логика: тема, бургер-меню, живой поиск, toast */

// ---------- Тема ----------
const themeToggle = document.getElementById('themeToggle');
function applyTheme(t) {
  document.documentElement.dataset.theme = t;
  localStorage.setItem('theme', t);
}
if (themeToggle) {
  themeToggle.addEventListener('click', () => {
    const cur = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    applyTheme(cur);
  });
}

// ---------- Бургер ----------
const burger = document.getElementById('burger');
if (burger) burger.addEventListener('click', () => {
  document.getElementById('mainNav').classList.toggle('open');
});

// ---------- Toast ----------
function toast(msg) {
  const el = document.createElement('div');
  el.className = 'toast';
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 2600);
}
window.toast = toast;

// ---------- Живой поиск в шапке ----------
(function () {
  const input = document.getElementById('searchInput');
  const dd = document.getElementById('searchDropdown');
  if (!input || !dd) return;
  let timer = null;

  async function fetchSuggestions(q) {
    try {
      const r = await fetch('/api/search?q=' + encodeURIComponent(q));
      const d = await r.json();
      let html = '';
      if (d.lessons.length) {
        html += '<div class="sd-title">Уроки</div>';
        d.lessons.forEach(l => html +=
          `<a class="sd-item" href="/lesson/${l.slug}">${esc(l.title)}<small>${esc(l.track_name)} · заглушка</small></a>`);
      }
      if (d.guides.length) {
        html += '<div class="sd-title">Руководства</div>';
        d.guides.forEach(g => html +=
          `<a class="sd-item" href="/guide/${g.slug}">${g.icon} ${esc(g.title)}</a>`);
      }
      if (!html) html = '<div class="sd-item muted">Ничего не найдено</div>';
      dd.innerHTML = html;
      dd.classList.remove('hidden');
    } catch (e) { /* ignore */ }
  }
  function esc(s) { return String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }

  input.addEventListener('input', () => {
    clearTimeout(timer);
    const q = input.value.trim();
    if (q.length < 2) { dd.classList.add('hidden'); return; }
    timer = setTimeout(() => fetchSuggestions(q), 250);
  });
  input.addEventListener('focus', () => {
    if (input.value.trim().length >= 2) fetchSuggestions(input.value.trim());
  });
  document.addEventListener('click', e => {
    if (!document.getElementById('searchBox').contains(e.target)) dd.classList.add('hidden');
  });
  // горячая клавиша "/"
  document.addEventListener('keydown', e => {
    if (e.key === '/' && document.activeElement !== input &&
        !['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)) {
      e.preventDefault(); input.focus();
    }
  });
})();
