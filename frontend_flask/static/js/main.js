/* Tab 切换 */
document.querySelectorAll('#tab-nav .tab').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('#tab-nav .tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    const id = 'panel-' + btn.dataset.tab;
    document.getElementById(id)?.classList.add('active');
    if (btn.dataset.tab === 'map') initMap();
    if (btn.dataset.tab === 'budget') initCharts();
  });
});

if (ACTIVE_TAB && ACTIVE_TAB !== 'itinerary') {
  const btn = document.querySelector(`[data-tab="${ACTIVE_TAB}"]`);
  if (btn) btn.click();
}

/* Toast 自动消失 */
const toast = document.getElementById('toast');
if (toast) {
  setTimeout(() => {
    toast.classList.add('fade-out');
    setTimeout(() => toast.remove(), 400);
  }, 3500);
}

/* 出发日期：确保有默认值，日历可点 */
(function initDateInput() {
  const el = document.getElementById('start-date');
  if (!el) return;
  if (!el.value) {
    el.value = typeof TODAY !== 'undefined' ? TODAY : new Date().toISOString().slice(0, 10);
  }
  el.addEventListener('click', () => {
    if (typeof el.showPicker === 'function') {
      try { el.showPicker(); } catch (_) { /* ignore */ }
    }
  });
})();

/* 左侧改参数未点生成 → 即时提示 */
(function watchFormStale() {
  const form = document.getElementById('generate-form');
  const hint = document.getElementById('client-stale-hint');
  if (!form || !hint || !form.dataset.planDays) return;

  const snapshot = () => ({
    days: form.querySelector('[name="days"]')?.value,
    city: form.querySelector('[name="city"]')?.value,
    budget: form.querySelector('[name="budget"]')?.value,
    date: form.querySelector('[name="start_date"]')?.value,
  });

  const baseline = {
    days: form.dataset.planDays,
    city: form.dataset.planCity,
    budget: form.dataset.planBudget,
    date: form.dataset.planDate,
  };

  const check = () => {
    const cur = snapshot();
    const stale = cur.days !== baseline.days || cur.city !== baseline.city
      || cur.budget !== baseline.budget || (cur.date && baseline.date && cur.date !== baseline.date);
    hint.classList.toggle('hidden', !stale);
  };

  form.addEventListener('input', check);
  form.addEventListener('change', check);
})();

/* 生成行程 Loading */
const AGENT_STEPS = [
  ['检索景点知识库…', 20],
  ['查询天气预报…', 40],
  ['计算预算分配…', 60],
  ['优化游览路线…', 80],
  ['生成完整行程…', 100],
];

function showLoading() {
  const overlay = document.getElementById('loading-overlay');
  const fill = document.getElementById('loading-fill');
  const step = document.getElementById('loading-step');
  if (!overlay) return;
  overlay.classList.remove('hidden');
  let i = 0;
  const tick = () => {
    if (i >= AGENT_STEPS.length) return;
    const [label, pct] = AGENT_STEPS[i];
    if (fill) fill.style.width = pct + '%';
    if (step) step.textContent = label;
    i += 1;
    setTimeout(tick, 350);
  };
  tick();
}

document.querySelectorAll('.js-loading-form').forEach(form => {
  form.addEventListener('submit', showLoading);
});

/* 高德地图 */
let mapInited = false;
let mapInstance = null;

function waitForVisible(el, cb, attempt = 0) {
  if (!el) return;
  const w = el.offsetWidth;
  const h = el.offsetHeight;
  const visible = el.getClientRects().length > 0;
  if (w > 0 && h > 0 && visible) {
    cb();
    return;
  }
  if (attempt > 40) {
    cb();
    return;
  }
  setTimeout(() => waitForVisible(el, cb, attempt + 1), 100);
}

function initMap() {
  if (mapInited || !MAP_POINTS.length) return;
  if (!HAS_AMAP || typeof AMap === 'undefined') return;

  const mapEl = document.getElementById('map');
  waitForVisible(mapEl, () => {
    if (mapInited) return;
    const center = CITY_CENTER || [MAP_POINTS[0].lng, MAP_POINTS[0].lat];
    const map = new AMap.Map('map', { zoom: 12, center, viewMode: '2D' });
    mapInstance = map;
    const path = [];

    MAP_POINTS.forEach((p, i) => {
      const pos = [p.lng, p.lat];
      path.push(pos);
      const marker = new AMap.Marker({
        position: pos,
        label: { content: String(i + 1), direction: 'top' },
      });
      const info = `<div style="padding:8px;max-width:220px;font-size:13px;">
        <b>${p.name || ''}</b><br>${p.time || ''}<br>${p.description || ''}</div>`;
      marker.on('click', () => {
        new AMap.InfoWindow({ content: info, offset: new AMap.Pixel(0, -28) }).open(map, pos);
      });
      map.add(marker);
    });

    if (path.length > 1) {
      map.add(new AMap.Polyline({
        path,
        strokeColor: '#4cc9f0',
        strokeWeight: 4,
        strokeStyle: 'dashed',
      }));
      map.setFitView();
    }

    if (SHOW_HEATMAP && HEATMAP_DATA.length && AMap.HeatMap) {
      const heatmap = new AMap.HeatMap(map, { radius: 28, opacity: [0, 0.65] });
      heatmap.setDataSet({ data: HEATMAP_DATA, max: 100 });
    }

    mapInited = true;
    setTimeout(() => map.resize(), 200);
    if (typeof ResizeObserver !== 'undefined') {
      new ResizeObserver(() => map.resize()).observe(mapEl);
    }
  });
}

/* 预算图表 */
let chartsInited = false;
const COLORS = ['#ff6b4a', '#ffd166', '#4cc9f0', '#06d6a0', '#94a3b8'];
const chartDefaults = {
  plugins: { legend: { labels: { color: '#e8ecf4' } } },
};

function initCharts() {
  if (chartsInited || !Object.keys(BUDGET).length) return;
  const labels = Object.keys(BUDGET);
  const values = Object.values(BUDGET);

  new Chart(document.getElementById('pie-chart'), {
    type: 'doughnut',
    data: { labels, datasets: [{ data: values, backgroundColor: COLORS, borderColor: '#0b1020', borderWidth: 2 }] },
    options: { ...chartDefaults, plugins: { ...chartDefaults.plugins, title: { display: true, text: '预算分配', color: '#e8ecf4' } } },
  });

  new Chart(document.getElementById('bar-chart'), {
    type: 'bar',
    data: {
      labels: DAYS_COST.map((_, i) => 'Day ' + (i + 1)),
      datasets: [{ label: '每日花费', data: DAYS_COST, backgroundColor: '#4cc9f0', borderRadius: 6 }],
    },
    options: {
      ...chartDefaults,
      plugins: { ...chartDefaults.plugins, title: { display: true, text: '每日花费对比', color: '#e8ecf4' } },
      scales: {
        x: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,107,74,0.1)' } },
        y: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,107,74,0.1)' } },
      },
    },
  });
  chartsInited = true;
}

/* 对话 */
const chatInput = document.getElementById('chat-input');
const chatSend = document.getElementById('chat-send');
const chatBox = document.getElementById('chat-box');

if (chatSend) {
  const send = async () => {
    const msg = chatInput.value.trim();
    if (!msg) return;
    chatInput.value = '';
    appendMsg('user', msg);
    chatSend.disabled = true;
    try {
      const res = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg }),
      });
      const data = await res.json();
      appendMsg('assistant', data.reply || '已收到');
      if (data.updated_plan) {
        appendMsg('assistant', '行程已更新，正在刷新…');
        setTimeout(() => location.reload(), 700);
      }
    } catch (e) {
      appendMsg('assistant', '请求失败：' + e.message);
    }
    chatSend.disabled = false;
  };
  chatSend.addEventListener('click', send);
  chatInput.addEventListener('keydown', e => { if (e.key === 'Enter') send(); });
}

function appendMsg(role, content) {
  const div = document.createElement('div');
  div.className = 'chat-msg ' + role;
  div.textContent = content;
  chatBox.appendChild(div);
  chatBox.scrollTop = chatBox.scrollHeight;
}
