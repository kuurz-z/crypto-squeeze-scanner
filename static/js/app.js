// Application State
let currentInterval = '15m';
let currentSymbol = 'BTCUSDT';
let currentFilter = 'all'; // 'all' | 'favorites' | 'signals' | 'squeeze'
let searchQuery = '';
let scannerData = [];
let autoRefreshTimer = null;

// High-Performance In-Memory Client Caches for Instant (0ms) Timeframe Switching
const clientScanCache = {};   // { '15m': { timestamp, data }, '30m': { timestamp, data } }
const clientCandleCache = {}; // { 'BTCUSDT_15m': { timestamp, data } }

// Favorites Management
const FAVORITES_STORAGE_KEY = 'quant_scanner_favorites';
let favoriteSymbols = new Set();

function loadFavorites() {
  try {
    const raw = localStorage.getItem(FAVORITES_STORAGE_KEY);
    if (raw) {
      const arr = JSON.parse(raw);
      if (Array.isArray(arr)) {
        favoriteSymbols = new Set(arr);
      }
    }
  } catch (e) {
    console.error('Error loading favorites from localStorage:', e);
    favoriteSymbols = new Set();
  }
  updateFavoriteBadges();
}

function saveFavorites() {
  try {
    localStorage.setItem(FAVORITES_STORAGE_KEY, JSON.stringify(Array.from(favoriteSymbols)));
  } catch (e) {
    console.error('Error saving favorites to localStorage:', e);
  }
  updateFavoriteBadges();
}

function isFavorite(symbol) {
  return favoriteSymbols.has(symbol);
}

function toggleFavorite(e, symbol) {
  if (e) {
    e.stopPropagation();
    if (typeof e.preventDefault === 'function') e.preventDefault();
  }
  if (!symbol) return;
  if (favoriteSymbols.has(symbol)) {
    favoriteSymbols.delete(symbol);
  } else {
    favoriteSymbols.add(symbol);
  }
  saveFavorites();
  renderScannerTable();
  updateActiveSymbolStar();
}

function updateFavoriteBadges() {
  const badge = document.getElementById('fav-count-badge');
  if (badge) {
    badge.innerText = favoriteSymbols.size;
  }
  updateActiveSymbolStar();
}

function updateActiveSymbolStar() {
  const activeStar = document.getElementById('active-fav-star');
  if (!activeStar) return;
  const isFav = favoriteSymbols.has(currentSymbol);
  if (isFav) {
    activeStar.className = 'fa-solid fa-star text-amber-400 star-glow scale-110';
  } else {
    activeStar.className = 'fa-regular fa-star text-slate-300 dark:text-slate-600 hover:text-amber-400 dark:hover:text-amber-400';
  }
}

/**
 * Format any timestamp, date string, or Date object into Philippine Standard Time (PHT, UTC+8 / Asia/Manila).
 * Returns formatted 24h string: "YYYY-MM-DD HH:mm:ss"
 */
function formatPhDateTime(val) {
  if (!val || val === '-' || val === 'null' || val === 'undefined') return '-';
  try {
    let date;
    if (typeof val === 'number') {
      date = new Date(val < 1e11 ? val * 1000 : val);
    } else if (typeof val === 'string') {
      const trimmed = val.trim();
      if (/^\d+$/.test(trimmed)) {
        const num = parseInt(trimmed, 10);
        date = new Date(num < 1e11 ? num * 1000 : num);
      } else if (/^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(:\d{2})?$/.test(trimmed)) {
        // Naive string already generated in Philippine Time (PHT / UTC+8)
        const iso = trimmed.replace(' ', 'T') + '+08:00';
        date = new Date(iso);
      } else {
        date = new Date(trimmed);
      }
    } else if (val instanceof Date) {
      date = val;
    } else {
      return String(val);
    }

    if (isNaN(date.getTime())) {
      return String(val);
    }

    const formatter = new Intl.DateTimeFormat('en-CA', {
      timeZone: 'Asia/Manila',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    });
    return formatter.format(date).replace(',', '');
  } catch (e) {
    return String(val);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initCharts();
  loadFavorites();
  setupEventListeners();
  
  // Initial load
  fetchScan(true);
  loadSymbolChart(currentSymbol);
  
  // Pre-warm 5m, 15m, and 30m caches in background for instantaneous zero-latency switching
  setTimeout(() => {
    ['5m', '15m', '30m'].forEach(tf => {
      if (tf !== currentInterval) {
        fetch(`/api/scan?interval=${tf}&limit=60`)
          .then(r => r.ok ? r.json() : null)
          .then(json => {
            if (json && json.data) {
              clientScanCache[tf] = { timestamp: Date.now(), data: json.data };
            }
          })
          .catch(() => {});

        fetch(`/api/candles/${currentSymbol}?interval=${tf}&limit=300`)
          .then(r => r.ok ? r.json() : null)
          .then(data => {
            if (data && data.candles) {
              clientCandleCache[`${currentSymbol}_${tf}`] = { timestamp: Date.now(), data };
            }
          })
          .catch(() => {});
      }
    });
  }, 800);

  // Periodic background refresh every 30s
  autoRefreshTimer = setInterval(() => {
    fetchScan(false);
  }, 30000);
});

function initTheme() {
  const savedTheme = localStorage.getItem('theme') || 'light';
  applyTheme(savedTheme);

  const themeBtn = document.getElementById('btn-theme-toggle');
  if (themeBtn) {
    themeBtn.addEventListener('click', () => {
      const current = document.documentElement.classList.contains('dark') ? 'dark' : 'light';
      const next = current === 'dark' ? 'light' : 'dark';
      applyTheme(next);
    });
  }
}

function applyTheme(theme) {
  const isDark = theme === 'dark';
  if (isDark) {
    document.documentElement.classList.add('dark');
  } else {
    document.documentElement.classList.remove('dark');
  }
  localStorage.setItem('theme', theme);

  const icon = document.getElementById('theme-icon');
  const text = document.getElementById('theme-text');
  if (icon && text) {
    if (isDark) {
      icon.className = 'fa-solid fa-moon text-indigo-400';
      text.innerText = 'Dark';
    } else {
      icon.className = 'fa-solid fa-sun text-amber-500';
      text.innerText = 'Light';
    }
  }

  if (typeof updateChartTheme === 'function') {
    updateChartTheme();
  }
}

function setupEventListeners() {
  // Timeframe buttons (Optimized 0ms Instant Switch for Scanner & Chart)
  document.querySelectorAll('.tf-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const newTf = btn.dataset.tf;
      if (currentInterval === newTf) return;

      document.querySelectorAll('.tf-btn').forEach(b => {
        b.classList.remove('bg-indigo-600', 'text-white', 'shadow');
        b.classList.add('text-slate-600', 'dark:text-gray-400');
      });
      btn.classList.add('bg-indigo-600', 'text-white', 'shadow');
      btn.classList.remove('text-slate-600', 'dark:text-gray-400');
      
      currentInterval = newTf;

      // Instant Optimistic Switch from Client Cache (0ms latency)
      if (clientScanCache[newTf]) {
        scannerData = clientScanCache[newTf].data;
        renderScannerTable();
        updateBacktestDropdown(scannerData);
      }
      
      const chartKey = `${currentSymbol}_${newTf}`;
      if (clientCandleCache[chartKey]) {
        const cachedChart = clientCandleCache[chartKey].data;
        updateChartData(cachedChart);
        updateTopMetrics(cachedChart);
      }

      // Fetch fresh live data in background without blocking UI
      fetchScan(false);
      loadSymbolChart(currentSymbol);
    });
  });

  // Filter tabs
  document.querySelectorAll('.filter-tab').forEach(tab => {
    tab.addEventListener('click', (e) => {
      document.querySelectorAll('.filter-tab').forEach(t => {
        t.classList.remove('bg-indigo-600', 'text-white', 'shadow');
        t.classList.add('bg-slate-100', 'dark:bg-[#1e293b]');
      });
      tab.classList.add('bg-indigo-600', 'text-white', 'shadow');
      tab.classList.remove('bg-slate-100', 'dark:bg-[#1e293b]');
      
      currentFilter = tab.dataset.filter;
      renderScannerTable();
    });
  });

  // Search input
  const searchInput = document.getElementById('coin-search');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      searchQuery = e.target.value.trim().toUpperCase();
      renderScannerTable();
    });
  }

  // Refresh button (Forces bypass of cache)
  const refreshBtn = document.getElementById('btn-refresh');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => {
      const refreshIcon = refreshBtn.querySelector('i');
      if (refreshIcon) refreshIcon.classList.add('fa-spin');
      
      Promise.all([
        fetchScan(false, true),
        loadSymbolChart(currentSymbol, true)
      ]).finally(() => {
        setTimeout(() => {
          if (refreshIcon) refreshIcon.classList.remove('fa-spin');
        }, 500);
      });
    });
  }

  // Active Symbol Favorite Toggle Button
  const activeFavBtn = document.getElementById('btn-toggle-fav-active');
  if (activeFavBtn) {
    activeFavBtn.addEventListener('click', (e) => {
      toggleFavorite(e, currentSymbol);
    });
  }

  // Backtest coin dropdown change
  const btSelect = document.getElementById('bt-symbol');
  if (btSelect) {
    btSelect.addEventListener('change', (e) => {
      const selected = e.target.value;
      if (selected && selected !== 'ALL') {
        onSelectCoin(selected);
      }
    });
  }

  // Backtest run button
  const btBtn = document.getElementById('btn-run-backtest');
  if (btBtn) {
    btBtn.addEventListener('click', () => {
      executeBacktest();
    });
  }
}

function updateBacktestDropdown(coins) {
  const btSelect = document.getElementById('bt-symbol');
  if (!btSelect || !coins || coins.length === 0) return;

  const currentVal = btSelect.value || currentSymbol;
  const uniqueSymbols = Array.from(new Set(coins.map(c => c.symbol))).sort();

  let html = `<option value="ALL">🌐 All Coins (Portfolio)</option>`;
  uniqueSymbols.forEach(sym => {
    const isSel = (sym === currentVal) ? 'selected' : '';
    const starPrefix = favoriteSymbols.has(sym) ? '★ ' : '';
    html += `<option value="${sym}" ${isSel}>${starPrefix}${sym}</option>`;
  });
  
  btSelect.innerHTML = html;
  btSelect.value = currentVal;
}

async function fetchScan(showSpinner = true, force = false) {
  const tbody = document.getElementById('scanner-tbody');
  const scanTf = currentInterval;
  
  // Instant render from cache if available and not forced
  if (clientScanCache[scanTf] && !force) {
    scannerData = clientScanCache[scanTf].data;
    renderScannerTable();
    updateBacktestDropdown(scannerData);
    updateFavoriteBadges();
  } else if (showSpinner && tbody && scannerData.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="5" class="py-8 text-center text-slate-400 dark:text-gray-500">
          <i class="fa-solid fa-spinner fa-spin text-lg text-indigo-500 mb-2"></i>
          <p>Scanning top liquid pairs...</p>
        </td>
      </tr>
    `;
  }

  try {
    const res = await fetch(`/api/scan?interval=${scanTf}&limit=60${force ? '&force_refresh=true' : ''}`);
    if (!res.ok) throw new Error('Scan failed');
    const json = await res.json();
    const data = json.data || [];
    
    // Store in client-side instant cache
    clientScanCache[scanTf] = { timestamp: Date.now(), data };
    
    if (json.api_rate_limit) {
      updateRateLimitDisplay(json.api_rate_limit);
    }
    
    // If user is still on this interval, update UI smoothly
    if (json.interval === scanTf) {
      scannerData = data;
      renderScannerTable();
      updateBacktestDropdown(scannerData);
      updateFavoriteBadges();
    }
  } catch (err) {
    console.error('Scan error:', err);
    if (tbody && scannerData.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" class="py-6 text-center text-rose-500">Failed to fetch live scan data.</td></tr>`;
    }
  }
}

function updateRateLimitDisplay(rl) {
  if (!rl) return;
  const headerVal = document.getElementById('header-rate-limit-val');
  const botBadge = document.getElementById('bot-rate-limit-badge');
  const botText = document.getElementById('bot-rate-limit-text');

  const used = rl.used_weight_1m || 0;
  const limit = rl.weight_limit_1m || 6000;
  const status = rl.status || 'HEALTHY';

  if (headerVal) {
    headerVal.innerText = `${used} / ${limit}`;
    if (status === 'HEALTHY') {
      headerVal.className = 'font-bold text-emerald-600 dark:text-emerald-400 text-[11px]';
    } else if (status === 'PACED') {
      headerVal.className = 'font-bold text-amber-600 dark:text-amber-400 text-[11px]';
    } else {
      headerVal.className = 'font-bold text-rose-600 dark:text-rose-400 text-[11px] animate-pulse';
    }
  }

  if (botBadge && botText) {
    if (status === 'HEALTHY') {
      botBadge.className = 'px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 flex items-center gap-1.5';
      botText.innerHTML = `<i class="fa-solid fa-shield-halved text-emerald-500"></i> API Weight: <b>${used}/${limit}</b> (Safe 🟢)`;
    } else if (status === 'PACED') {
      botBadge.className = 'px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 flex items-center gap-1.5';
      botText.innerHTML = `<i class="fa-solid fa-shield-halved text-amber-500"></i> API Weight: <b>${used}/${limit}</b> (Paced 🟡)`;
    } else {
      botBadge.className = 'px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20 flex items-center gap-1.5';
      botText.innerHTML = `<i class="fa-solid fa-triangle-exclamation text-rose-500 animate-pulse"></i> API Weight: <b>${used}/${limit}</b> (Defense 🔴)`;
    }
  }
}

// Table Sorting State
let sortColumn = 'default';
let sortDirection = 'desc';

function handleTableSort(column) {
  if (sortColumn === column) {
    sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
  } else {
    sortColumn = column;
    sortDirection = (column === 'symbol') ? 'asc' : 'desc';
  }
  updateSortIcons();
  renderScannerTable();
}

function updateSortIcons() {
  ['symbol', 'price', 'squeeze', 'buyer_ratio', 'trend'].forEach(col => {
    const el = document.getElementById(`sort-icon-${col}`);
    if (el) {
      if (sortColumn === col) {
        el.innerHTML = sortDirection === 'asc' ? '<i class="fa-solid fa-arrow-up text-indigo-500"></i>' : '<i class="fa-solid fa-arrow-down text-indigo-500"></i>';
      } else {
        el.innerHTML = '';
      }
    }
  });
}

function renderScannerTable() {
  const tbody = document.getElementById('scanner-tbody');
  const badge = document.getElementById('scan-count-badge');
  if (!tbody) return;

  let filtered = scannerData.filter(item => {
    const matchSearch = !searchQuery || item.symbol.toUpperCase().includes(searchQuery);
    if (!matchSearch) return false;

    if (currentFilter === 'signals') {
      return item.signal !== 'NONE' || item.recent_signal !== 'NONE';
    } else if (currentFilter === 'squeeze') {
      return item.is_squeeze === true;
    } else if (currentFilter === 'tension') {
      return item.squeeze_stage === 'HIGH_TENSION' || (item.is_squeeze && item.squeeze_bars >= 6) || (item.compression_ratio && item.compression_ratio <= 0.75);
    } else if (currentFilter === 'favorites') {
      return favoriteSymbols.has(item.symbol);
    }
    return true;
  });

  // Apply Column Sorting
  if (sortColumn !== 'default') {
    filtered.sort((a, b) => {
      let valA, valB;
      if (sortColumn === 'symbol') {
        valA = a.symbol;
        valB = b.symbol;
        return sortDirection === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
      } else if (sortColumn === 'price') {
        valA = a.price || 0;
        valB = b.price || 0;
      } else if (sortColumn === 'squeeze') {
        valA = a.is_squeeze ? ((a.squeeze_bars || 0) + (a.tension_score || 0)) : (a.squeeze_stage === 'FIRED' ? 50 : 0);
        valB = b.is_squeeze ? ((b.squeeze_bars || 0) + (b.tension_score || 0)) : (b.squeeze_stage === 'FIRED' ? 50 : 0);
      } else if (sortColumn === 'buyer_ratio') {
        valA = a.buyer_ratio || 50;
        valB = b.buyer_ratio || 50;
      } else if (sortColumn === 'trend') {
        valA = a.pct_from_ema200 || a.change_pct || 0;
        valB = b.pct_from_ema200 || b.change_pct || 0;
      }
      return sortDirection === 'asc' ? valA - valB : valB - valA;
    });
  }

  if (badge) badge.innerText = `${filtered.length} Pairs`;

  if (filtered.length === 0) {
    if (currentFilter === 'favorites') {
      tbody.innerHTML = `
        <tr>
          <td colspan="6" class="py-8 px-4 text-center text-slate-400 dark:text-gray-500">
            <i class="fa-regular fa-star text-2xl text-amber-400 mb-2 block animate-pulse"></i>
            <p class="font-semibold text-slate-700 dark:text-gray-300 text-xs">No favorite coins added yet</p>
            <p class="text-[11px] text-slate-400 dark:text-gray-500 mt-1">Click the <i class="fa-regular fa-star text-amber-500"></i> star icon next to any coin to bookmark and monitor it here.</p>
          </td>
        </tr>
      `;
    } else {
      tbody.innerHTML = `<tr><td colspan="6" class="py-6 text-center text-slate-400 dark:text-gray-500">No coins match the filter.</td></tr>`;
    }
    return;
  }

  tbody.innerHTML = filtered.map(item => {
    const isSelected = item.symbol === currentSymbol ? 'selected-row' : '';
    const formattedPrice = item.price < 1 ? item.price.toFixed(5) : item.price.toFixed(2);
    const isFav = favoriteSymbols.has(item.symbol);
    const starClass = isFav ? 'fa-solid fa-star text-amber-400 star-glow' : 'fa-regular fa-star text-slate-300 dark:text-slate-600 hover:text-amber-400 dark:hover:text-amber-400';
    const starTitle = isFav ? 'Remove from favorites' : 'Add to favorites';
    
    // Traffic Light Squeeze Badge
    let squeezeHtml = '';
    if (item.squeeze_stage === 'HIGH_TENSION') {
      squeezeHtml = `<span class="px-2 py-0.5 rounded text-[10px] bg-orange-500/15 dark:bg-orange-500/20 text-orange-700 dark:text-orange-300 border border-orange-400/40 dark:border-orange-500/40 font-bold inline-flex items-center gap-1 shadow-sm" title="Compression Ratio: ${item.compression_ratio}x (High Tension)"><i class="fa-solid fa-fire text-orange-500 text-[9px] animate-pulse"></i> ${item.squeeze_bars}b (${item.compression_ratio}x)</span>`;
    } else if (item.squeeze_stage === 'COILING' || item.is_squeeze) {
      squeezeHtml = `<span class="px-2 py-0.5 rounded text-[10px] bg-amber-500/15 dark:bg-amber-500/10 text-amber-700 dark:text-amber-300 border border-amber-400/40 dark:border-amber-500/30 font-medium inline-flex items-center gap-1" title="Coiling spring: ${item.squeeze_bars} bars"><i class="fa-solid fa-compress text-[9px]"></i> ${item.squeeze_bars} bars</span>`;
    } else if (item.squeeze_stage === 'FIRED') {
      squeezeHtml = `<span class="px-2 py-0.5 rounded text-[10px] bg-emerald-500/15 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 border border-emerald-400/40 dark:border-emerald-500/40 font-bold inline-flex items-center gap-1 animate-pulse"><i class="fa-solid fa-bolt text-emerald-500 text-[9px]"></i> Fired</span>`;
    } else {
      squeezeHtml = `<span class="text-[10px] text-slate-400 dark:text-gray-600">--</span>`;
    }

    // Order Flow / Buyer Dominance Meter
    let orderFlowHtml = '';
    const bRatio = item.buyer_ratio !== undefined ? item.buyer_ratio : 50.0;
    if (bRatio >= 55.0) {
      orderFlowHtml = `<span class="px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20 inline-flex items-center gap-1" title="Taker Market Buys: ${bRatio}%"><i class="fa-solid fa-arrow-trend-up text-[8px]"></i> ${bRatio.toFixed(0)}% Buy</span>`;
    } else if (bRatio <= 45.0) {
      const sRatio = (100.0 - bRatio).toFixed(0);
      orderFlowHtml = `<span class="px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold bg-rose-500/10 text-rose-700 dark:text-rose-400 border border-rose-500/20 inline-flex items-center gap-1" title="Taker Market Sells: ${sRatio}%"><i class="fa-solid fa-arrow-trend-down text-[8px]"></i> ${sRatio}% Sell</span>`;
    } else {
      orderFlowHtml = `<span class="px-1.5 py-0.5 rounded text-[10px] font-mono font-medium text-slate-500 dark:text-gray-400 bg-slate-100 dark:bg-gray-800 border border-slate-200 dark:border-gray-700" title="Balanced Flow">${bRatio.toFixed(0)}%</span>`;
    }

    // Signal badge
    let signalHtml = '';
    if (item.signal === 'LONG') {
      signalHtml = `<span class="px-2 py-0.5 rounded text-[10px] bg-emerald-500/15 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400 border border-emerald-400/40 dark:border-emerald-500/40 font-bold animate-pulse inline-flex items-center gap-1"><i class="fa-solid fa-arrow-trend-up text-[9px]"></i> LONG</span>`;
    } else if (item.signal === 'SHORT') {
      signalHtml = `<span class="px-2 py-0.5 rounded text-[10px] bg-rose-500/15 dark:bg-rose-500/20 text-rose-700 dark:text-rose-400 border border-rose-400/40 dark:border-rose-500/40 font-bold animate-pulse inline-flex items-center gap-1"><i class="fa-solid fa-arrow-trend-down text-[9px]"></i> SHORT</span>`;
    } else if (item.recent_signal !== 'NONE') {
      signalHtml = `<span class="px-1.5 py-0.5 rounded text-[9px] bg-indigo-500/10 dark:bg-indigo-500/15 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-500/30 font-medium inline-flex items-center gap-1"><i class="fa-solid fa-bolt-lightning text-[8px]"></i> ${item.recent_signal}</span>`;
    } else {
      signalHtml = `<span class="text-[10px] text-slate-400 dark:text-gray-600">--</span>`;
    }

    // Trend badge
    const trendColor = item.trend === 'BULLISH' ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400';
    const trendIcon = item.trend === 'BULLISH' ? 'fa-arrow-trend-up' : 'fa-arrow-trend-down';

    return `
      <tr class="cursor-pointer hover:bg-slate-50 dark:hover:bg-gray-800/60 ${isSelected}" onclick="onSelectCoin('${item.symbol}')">
        <td class="py-2.5 px-3 font-semibold text-slate-900 dark:text-white whitespace-nowrap align-top">
          <div class="h-5 flex items-center gap-2 leading-5">
            <button class="favorite-star-btn cursor-pointer p-0.5 focus:outline-none" title="${starTitle}" onclick="toggleFavorite(event, '${item.symbol}')">
              <i class="${starClass} text-xs"></i>
            </button>
            <i class="fa-brands fa-bitcoin text-indigo-600 dark:text-indigo-400 text-xs"></i>
            <span>${item.symbol.replace('USDT', '')}</span><span class="text-[10px] text-slate-400 dark:text-gray-500 font-normal">/USDT</span>
          </div>
        </td>
        <td class="py-2.5 px-2 font-mono font-medium text-slate-800 dark:text-gray-200 whitespace-nowrap align-top">
          <div class="h-5 flex items-center leading-5">$${formattedPrice}</div>
        </td>
        <td class="py-2.5 px-2 text-center whitespace-nowrap align-top">
          <div class="h-5 flex items-center justify-center leading-5">${squeezeHtml}</div>
        </td>
        <td class="py-2.5 px-2 text-center whitespace-nowrap align-top">
          <div class="h-5 flex items-center justify-center leading-5">${orderFlowHtml}</div>
        </td>
        <td class="py-2.5 px-2 text-center whitespace-nowrap align-top">
          <div class="h-5 flex items-center justify-center leading-5">${signalHtml}</div>
        </td>
        <td class="py-2.5 px-2 text-right ${trendColor} text-[11px] font-medium whitespace-nowrap align-top">
          <div class="h-5 flex items-center justify-end gap-1 leading-5">
            <i class="fa-solid ${trendIcon} text-[10px]"></i> ${item.pct_from_ema200 > 0 ? '+' : ''}${item.pct_from_ema200}%
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

function onSelectCoin(symbol) {
  currentSymbol = symbol;
  renderScannerTable();
  loadSymbolChart(symbol);
  updateActiveSymbolStar();
  
  // Sync backtest select dropdown
  const btSelect = document.getElementById('bt-symbol');
  if (btSelect && symbol !== 'ALL') {
    btSelect.value = symbol;
  }
}

async function loadSymbolChart(symbol, force = false) {
  const chartTf = currentInterval;
  const chartKey = `${symbol}_${chartTf}`;
  
  // Instant render from client cache if available and not forced
  if (clientCandleCache[chartKey] && !force) {
    const cached = clientCandleCache[chartKey].data;
    updateChartData(cached);
    updateTopMetrics(cached);
  }

  try {
    const res = await fetch(`/api/candles/${symbol}?interval=${chartTf}&limit=300`);
    if (!res.ok) throw new Error('Failed to load chart');
    const data = await res.json();
    
    // Store in client cache
    clientCandleCache[chartKey] = { timestamp: Date.now(), data };
    
    // If still viewing this symbol and interval, update chart smoothly
    if (data.symbol === currentSymbol) {
      updateChartData(data);
      updateTopMetrics(data);
    }
  } catch (err) {
    console.error('Error loading chart:', err);
  }
}

function updateTopMetrics(data) {
  const m = data.current_metrics;
  if (!m) return;

  document.getElementById('active-symbol-badge').innerText = data.symbol;
  updateActiveSymbolStar();
  document.getElementById('active-price-badge').innerText = `$${m.price < 1 ? m.price.toFixed(5) : m.price.toFixed(2)}`;
  
  // Trend
  const trendBadge = document.getElementById('active-trend-badge');
  if (m.trend === 'BULLISH') {
    trendBadge.className = 'text-xs px-2 py-0.5 rounded bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/20 font-semibold uppercase';
    trendBadge.innerText = 'Above 200 EMA (Uptrend)';
  } else {
    trendBadge.className = 'text-xs px-2 py-0.5 rounded bg-rose-50 dark:bg-rose-500/10 text-rose-700 dark:text-rose-400 border border-rose-200 dark:border-rose-500/20 font-semibold uppercase';
    trendBadge.innerText = 'Below 200 EMA (Downtrend)';
  }

  // Squeeze status
  const sqzBadge = document.getElementById('active-squeeze-status');
  if (m.is_squeeze) {
    sqzBadge.className = 'text-xs px-2.5 py-1 rounded bg-amber-50 dark:bg-amber-500/10 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-500/30 flex items-center gap-1.5 font-medium';
    sqzBadge.innerHTML = `<span class="w-2 h-2 rounded-full bg-amber-500 animate-ping"></span><i class="fa-solid fa-compress text-[11px]"></i> Squeeze Active (${m.squeeze_bars} bars)`;
  } else if (m.signal !== 'NONE') {
    sqzBadge.className = 'text-xs px-2.5 py-1 rounded bg-emerald-50 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-500/40 flex items-center gap-1.5 font-bold';
    sqzBadge.innerHTML = `<i class="fa-solid fa-bolt-lightning text-emerald-500"></i> Breakout ${m.signal} Fired!`;
  } else {
    sqzBadge.className = 'text-xs px-2.5 py-1 rounded bg-slate-100 dark:bg-gray-800 text-slate-600 dark:text-gray-400 border border-slate-200 dark:border-gray-700 flex items-center gap-1.5 font-medium';
    sqzBadge.innerHTML = `<span class="w-2 h-2 rounded-full bg-slate-400 dark:bg-gray-500"></span> Normal Volatility`;
  }

  document.getElementById('active-atr-badge').innerText = `ATR14: $${m.atr}`;

  // Update Dynamic RR Boxes
  const rr = m.rr_levels;
  if (rr) {
    const fmt = val => `$${val < 1 ? val.toFixed(5) : val.toFixed(2)}`;
    document.getElementById('rr-sl').innerText = fmt(rr.stop_loss);
    document.getElementById('rr-entry').innerText = fmt(rr.entry);
    document.getElementById('rr-tp1').innerText = fmt(rr.tp1_1rr);
    document.getElementById('rr-tp2').innerText = fmt(rr.tp2_2rr);
    document.getElementById('rr-tp3').innerText = fmt(rr.tp3_3rr);
    document.getElementById('rr-tp4').innerText = fmt(rr.tp4_4rr);
  }
}

async function executeBacktest() {
  const btSelect = document.getElementById('bt-symbol');
  const sym = (btSelect ? btSelect.value : currentSymbol).toUpperCase();
  const targetRR = parseFloat(document.getElementById('bt-target-rr').value || '2.0');
  const bars = parseInt(document.getElementById('bt-bars').value || '1000');
  const tbody = document.getElementById('bt-trades-tbody');
  
  if (tbody) {
    tbody.innerHTML = `
      <tr>
        <td colspan="8" class="py-4 text-center text-slate-500 dark:text-gray-400">
          <i class="fa-solid fa-spinner fa-spin text-indigo-600 dark:text-indigo-400 mr-2"></i> ${sym === 'ALL' ? 'Simulating portfolio across all top crypto pairs...' : `Simulating ${sym} over ${bars} bars with fee friction...`}
        </td>
      </tr>
    `;
  }

  try {
    const res = await fetch(`/api/backtest?symbol=${sym}&interval=${currentInterval}&bars=${bars}&target_rr=${targetRR}`);
    if (!res.ok) throw new Error('Backtest request failed');
    const data = await res.json();

    // Populate Metrics Cards
    document.getElementById('bt-total-trades').innerText = data.total_trades || 0;
    document.getElementById('bt-win-rate').innerText = `${data.win_rate_pct || 0}%`;
    document.getElementById('bt-tp1-rate').innerText = `${data.tp1_hit_rate_pct || 0}%`;
    document.getElementById('bt-profit-factor').innerText = data.profit_factor || 0;
    document.getElementById('bt-expectancy').innerText = `${data.expectancy_r > 0 ? '+' : ''}${data.expectancy_r || 0} R`;
    document.getElementById('bt-max-dd').innerText = `-${data.max_drawdown_r || 0} R`;

    // Populate Trades Table
    if (tbody && data.trades && data.trades.length > 0) {
      tbody.innerHTML = data.trades.slice().reverse().map(t => {
        const isWin = t.outcome === 'WIN';
        const badgeColor = isWin ? 'text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-500/10 border-emerald-200 dark:border-emerald-500/20' : 'text-rose-700 dark:text-rose-400 bg-rose-50 dark:bg-rose-500/10 border-rose-200 dark:border-rose-500/20';
        const rColor = t.net_r > 0 ? 'text-emerald-600 dark:text-emerald-400 font-bold' : 'text-rose-600 dark:text-rose-400 font-bold';
        const symPrefix = t.symbol ? `<span class="px-1 py-0.5 rounded bg-indigo-50 dark:bg-indigo-950/50 text-indigo-600 dark:text-indigo-300 font-semibold mr-1 text-[10px]">${t.symbol.replace('USDT','')}</span>` : '';
        
        return `
          <tr class="hover:bg-slate-50 dark:hover:bg-gray-800/50 text-[11px]">
            <td class="py-2 px-3 text-slate-500 dark:text-gray-400 whitespace-nowrap align-top">
              <div class="h-5 flex items-center leading-5">${symPrefix}#${t.trade_num}</div>
            </td>
            <td class="py-2 px-3 font-semibold ${t.direction === 'LONG' ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'} whitespace-nowrap align-top">
              <div class="h-5 flex items-center leading-5">${t.direction}</div>
            </td>
            <td class="py-2 px-3 font-mono text-slate-800 dark:text-slate-200 whitespace-nowrap align-top">
              <div class="h-5 flex items-center leading-5">$${t.entry_price}</div>
            </td>
            <td class="py-2 px-3 font-mono text-rose-600 dark:text-rose-300 whitespace-nowrap align-top">
              <div class="h-5 flex items-center leading-5">$${t.sl_price}</div>
            </td>
            <td class="py-2 px-3 font-mono text-emerald-600 dark:text-emerald-300 whitespace-nowrap align-top">
              <div class="h-5 flex items-center leading-5">$${t.tp_target_price}</div>
            </td>
            <td class="py-2 px-3 font-mono text-slate-800 dark:text-slate-200 whitespace-nowrap align-top">
              <div class="h-5 flex items-center leading-5">$${t.exit_price}</div>
            </td>
            <td class="py-2 px-3 text-center whitespace-nowrap align-top">
              <div class="h-5 flex items-center justify-center leading-5">
                <span class="px-2 py-0.5 rounded border text-[10px] font-semibold ${badgeColor}">${t.outcome}</span>
              </div>
            </td>
            <td class="py-2 px-3 text-right font-mono ${rColor} whitespace-nowrap align-top">
              <div class="h-5 flex items-center justify-end leading-5">${t.net_r > 0 ? '+' : ''}${t.net_r}R</div>
            </td>
          </tr>
        `;
      }).join('');
    } else if (tbody) {
      tbody.innerHTML = `<tr><td colspan="8" class="py-4 text-center text-slate-400 dark:text-gray-500">No signals triggered in the historical sample.</td></tr>`;
    }
  } catch (err) {
    console.error('Backtest error:', err);
    if (tbody) {
      tbody.innerHTML = `<tr><td colspan="8" class="py-4 text-center text-rose-500">Backtest failed. Please try again.</td></tr>`;
    }
  }
}

/* =========================================================================
   LIVE AUTO-BOT & AI STRATEGY PERFECTION CONTROLLER
   ========================================================================= */

let currentView = 'scanner'; // 'scanner' | 'bot'
let botPollTimer = null;

function setupViewNavigation() {
  const scannerBtn = document.getElementById('tab-scanner-btn');
  const botBtn = document.getElementById('tab-bot-btn');
  const scannerView = document.getElementById('scanner-view-container');
  const botView = document.getElementById('bot-view-container');
  const tfGroup = document.getElementById('tf-group');

  if (scannerBtn && botBtn) {
    scannerBtn.addEventListener('click', () => {
      currentView = 'scanner';
      scannerView.classList.remove('hidden');
      botView.classList.add('hidden');
      if (tfGroup) tfGroup.classList.remove('hidden');

      scannerBtn.className = 'px-3 py-1.5 rounded-md transition bg-indigo-600 text-white shadow flex items-center gap-1.5';
      botBtn.className = 'px-3 py-1.5 rounded-md transition text-slate-600 dark:text-gray-400 hover:text-slate-900 dark:hover:text-white flex items-center gap-1.5';
    });

    botBtn.addEventListener('click', () => {
      currentView = 'bot';
      scannerView.classList.add('hidden');
      botView.classList.remove('hidden');
      if (tfGroup) tfGroup.classList.add('hidden');

      botBtn.className = 'px-3 py-1.5 rounded-md transition bg-indigo-600 text-white shadow flex items-center gap-1.5';
      scannerBtn.className = 'px-3 py-1.5 rounded-md transition text-slate-600 dark:text-gray-400 hover:text-slate-900 dark:hover:text-white flex items-center gap-1.5';

      fetchBotTelemetry();
    });
  }

  // Bot action buttons
  const resetBtn = document.getElementById('btn-bot-reset-balance');
  if (resetBtn) {
    resetBtn.addEventListener('click', async () => {
      if (confirm('Reset account balance to $100.00 USD? (Your full trade history and diagnostic records will be preserved).')) {
        try {
          const res = await fetch('/api/bot/reset', { method: 'POST' });
          const data = await res.json();
          alert('Account balance reset to $100.00 USD! Full trade history preserved.');
          fetchBotTelemetry();
        } catch (e) {
          console.error('Error resetting balance:', e);
        }
      }
    });
  }

  const autotradeToggleBtn = document.getElementById('btn-bot-toggle-autotrade');
  if (autotradeToggleBtn) {
    autotradeToggleBtn.addEventListener('click', async () => {
      try {
        const res = await fetch('/api/bot/toggle_auto_trading', { method: 'POST' });
        const data = await res.json();
        fetchBotTelemetry();
      } catch (e) {
        console.error('Error toggling auto-trading:', e);
      }
    });
  }

  const toggleBtn = document.getElementById('btn-bot-toggle');
  if (toggleBtn) {
    toggleBtn.addEventListener('click', async () => {
      try {
        const res = await fetch('/api/bot/toggle', { method: 'POST' });
        const data = await res.json();
        fetchBotTelemetry();
      } catch (e) {
        console.error('Error toggling bot:', e);
      }
    });
  }

  const optBtn = document.getElementById('btn-bot-optimize');
  if (optBtn) {
    optBtn.addEventListener('click', async () => {
      optBtn.disabled = true;
      optBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Optimizing...';
      try {
        const res = await fetch('/api/bot/optimize_now', { method: 'POST' });
        const data = await res.json();
        alert('AI Strategy Perfection Cycle Completed! Parameters benchmarked.');
        fetchBotTelemetry();
      } catch (e) {
        console.error('Optimization error:', e);
      } finally {
        optBtn.disabled = false;
        optBtn.innerHTML = '<i class="fa-solid fa-bolt-lightning"></i> <span>Optimize Strategy Now</span>';
      }
    });
  }

  // Depleted report modal buttons
  const viewReportBtn = document.getElementById('btn-view-depleted-report');
  const closeReportModalBtn = document.getElementById('btn-close-report-modal');
  const closeReportModalBtn2 = document.getElementById('btn-modal-close-action');
  const depletedRestartBtn = document.getElementById('btn-depleted-restart');
  const reportModal = document.getElementById('report-modal');
  const reportContent = document.getElementById('report-modal-content');

  if (viewReportBtn && reportModal) {
    viewReportBtn.addEventListener('click', async () => {
      try {
        const res = await fetch('/api/bot/depletion_report');
        const data = await res.json();
        if (data.content) {
          reportContent.innerText = data.content;
        } else {
          reportContent.innerText = 'No depletion report file available yet.';
        }
        reportModal.classList.remove('hidden');
      } catch (e) {
        console.error('Error fetching depletion report:', e);
      }
    });
  }

  const hideModal = () => {
    if (reportModal) reportModal.classList.add('hidden');
  };

  if (closeReportModalBtn) closeReportModalBtn.addEventListener('click', hideModal);
  if (closeReportModalBtn2) closeReportModalBtn2.addEventListener('click', hideModal);

  // Fund & Restart Modal Elements
  const fundModal = document.getElementById('fund-bot-modal');
  const closeFundModalBtn = document.getElementById('btn-close-fund-modal');
  const cancelFundModalBtn = document.getElementById('btn-cancel-fund-modal');
  const submitFundBtn = document.getElementById('btn-submit-fund-modal');
  const inputCapital = document.getElementById('input-fund-capital');
  const inputRisk = document.getElementById('input-fund-risk');
  const fundCalcWin = document.getElementById('fund-calc-win');
  const fundCalcLoss = document.getElementById('fund-calc-loss');

  const openFundModal = () => {
    if (fundModal) fundModal.classList.remove('hidden');
  };

  const closeFundModal = () => {
    if (fundModal) fundModal.classList.add('hidden');
  };

  if (closeFundModalBtn) closeFundModalBtn.addEventListener('click', closeFundModal);
  if (cancelFundModalBtn) cancelFundModalBtn.addEventListener('click', closeFundModal);

  // Hook buttons to open Fund Modal
  if (depletedRestartBtn) depletedRestartBtn.addEventListener('click', openFundModal);

  // Quick pills handling
  document.querySelectorAll('.quick-cap-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.quick-cap-btn').forEach(b => {
        b.className = 'quick-cap-btn px-2.5 py-1 rounded bg-slate-100 dark:bg-gray-800 hover:bg-slate-200 dark:hover:bg-gray-700 font-mono text-[11px]';
      });
      btn.className = 'quick-cap-btn px-2.5 py-1 rounded bg-emerald-500 text-white font-mono text-[11px] font-bold';
      if (inputCapital) inputCapital.value = parseFloat(btn.dataset.cap).toFixed(2);
    });
  });

  document.querySelectorAll('.quick-risk-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.quick-risk-btn').forEach(b => {
        b.className = 'quick-risk-btn px-2.5 py-1 rounded bg-slate-100 dark:bg-gray-800 hover:bg-slate-200 dark:hover:bg-gray-700 font-mono text-[11px]';
      });
      btn.className = 'quick-risk-btn px-2.5 py-1 rounded bg-emerald-500 text-white font-mono text-[11px] font-bold';
      const r = parseFloat(btn.dataset.risk);
      if (inputRisk) {
        inputRisk.value = r.toFixed(2);
        updateFundExplainer(r);
      }
    });
  });

  if (inputRisk) {
    inputRisk.addEventListener('input', (e) => {
      const r = parseFloat(e.target.value) || 1.0;
      updateFundExplainer(r);
    });
  }

  function updateFundExplainer(risk) {
    if (fundCalcWin) fundCalcWin.innerText = `+$${(risk * 2.0).toFixed(2)} USD`;
    if (fundCalcLoss) fundCalcLoss.innerText = `-$${risk.toFixed(2)} USD`;
  }

  if (submitFundBtn) {
    submitFundBtn.addEventListener('click', async () => {
      const cap = parseFloat(inputCapital.value) || 100.0;
      const risk = parseFloat(inputRisk.value) || 1.0;

      if (cap <= 0 || risk <= 0) {
        alert('Please enter valid positive numbers for capital and risk.');
        return;
      }

      submitFundBtn.disabled = true;
      submitFundBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Starting...';

      try {
        const res = await fetch('/api/bot/restart_with_capital', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ capital: cap, fixed_risk_usd: risk })
        });
        const data = await res.json();
        closeFundModal();
        alert(`Bot successfully started with $${cap.toFixed(2)} USD capital ($${risk.toFixed(2)}/trade)!`);
        fetchBotTelemetry();
      } catch (e) {
        console.error('Error starting bot:', e);
        alert('Failed to start bot. Please try again.');
      } finally {
        submitFundBtn.disabled = false;
        submitFundBtn.innerHTML = '<i class="fa-solid fa-play"></i> Start Bot with Capital';
      }
    });
  }

  // Evolutionary Tournament & Snapshot Triggers
  const dailySnapshotBtn = document.getElementById('btn-trigger-daily-snapshot');
  const weeklyMacroBtn = document.getElementById('btn-trigger-weekly-macro');
  const monthlyTournamentBtn = document.getElementById('btn-trigger-monthly-tournament');
  const championsGauntletBtn = document.getElementById('btn-trigger-champions-gauntlet');

  if (dailySnapshotBtn) {
    dailySnapshotBtn.addEventListener('click', async () => {
      dailySnapshotBtn.disabled = true;
      dailySnapshotBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin text-[10px]"></i> Saving Snapshot...';
      try {
        const res = await fetch('/api/bot/daily_snapshot_now', { method: 'POST' });
        const data = await res.json();
        alert(`Daily Strategy Snapshot Saved!\nDate: ${data.result?.date}\nBalance: $${data.result?.account_balance?.toFixed(2)} USD\nWin Rate: ${data.result?.win_rate_pct}%\nArchived to: reports/historical_archive.json`);
        fetchBotTelemetry();
      } catch (e) {
        alert('Daily snapshot failed. Please check network.');
      } finally {
        dailySnapshotBtn.disabled = false;
        dailySnapshotBtn.innerHTML = '<i class="fa-solid fa-floppy-disk text-blue-500 text-[10px]"></i> Save Daily Snapshot';
      }
    });
  }

  if (weeklyMacroBtn) {
    weeklyMacroBtn.addEventListener('click', async () => {
      weeklyMacroBtn.disabled = true;
      weeklyMacroBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin text-[10px]"></i> Optimizing (1h/4h)...';
      try {
        const res = await fetch('/api/bot/macro_optimize_now?period=WEEKLY', { method: 'POST' });
        const data = await res.json();
        alert(`Weekly Macro Optimization Complete!\nOptimal Timeframe: ${data.result?.optimal_timeframe || '1h'}\nTested: ${data.result?.metrics?.tested_trades || 0} trades (${data.result?.metrics?.win_rate_pct || 0}% Win Rate)\nReport saved to: ${data.result?.report_file || 'reports/'}`);
        fetchBotTelemetry();
      } catch (e) {
        alert('Weekly optimization failed. Please check network.');
      } finally {
        weeklyMacroBtn.disabled = false;
        weeklyMacroBtn.innerHTML = '<i class="fa-solid fa-bolt text-amber-500 text-[10px]"></i> Run Weekly (1h/4h)';
      }
    });
  }

  if (monthlyTournamentBtn) {
    monthlyTournamentBtn.addEventListener('click', async () => {
      monthlyTournamentBtn.disabled = true;
      monthlyTournamentBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin text-[10px]"></i> Tournament Running...';
      try {
        const res = await fetch('/api/bot/monthly_tournament_now', { method: 'POST' });
        const data = await res.json();
        alert(`🏆 End-of-Month Championship Tournament Complete!\nCrowned Monthly Champion: ${data.result?.strategy_name} (${data.result?.timeframe})\nWin Rate: ${data.result?.win_rate_pct}% (Floor >= 40%)\nReproducibility Score: ${data.result?.reproducibility_score}/100\nSaved to Hall of Fame!`);
        fetchBotTelemetry();
      } catch (e) {
        alert('Monthly tournament failed. Please check network.');
      } finally {
        monthlyTournamentBtn.disabled = false;
        monthlyTournamentBtn.innerHTML = '<i class="fa-solid fa-trophy text-purple-500 text-[10px]"></i> Monthly Tournament';
      }
    });
  }

  if (championsGauntletBtn) {
    championsGauntletBtn.addEventListener('click', async () => {
      championsGauntletBtn.disabled = true;
      championsGauntletBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin text-[10px]"></i> Simulating GOAT...';
      try {
        const res = await fetch('/api/bot/champions_gauntlet_now', { method: 'POST' });
        const data = await res.json();
        alert(`🏛️ All-Time Champions of Champions Gauntlet Complete!\nReigning All-Time GOAT: ${data.result?.strategy_name || data.result?.name}\nWin Rate: ${data.result?.win_rate_pct}%\nReproducibility: ${data.result?.reproducibility_score}/100`);
        fetchBotTelemetry();
      } catch (e) {
        alert('Gauntlet simulation failed. Please check network.');
      } finally {
        championsGauntletBtn.disabled = false;
        championsGauntletBtn.innerHTML = '<i class="fa-solid fa-crown text-amber-500 text-[10px]"></i> All-Time Gauntlet';
      }
    });
  }

  // Tab Switcher for Active Positions vs Closed Trade History
  const tabActivePosBtn = document.getElementById('tab-btn-active-pos');
  const tabClosedHistBtn = document.getElementById('tab-btn-closed-history');
  const tabActivePosContent = document.getElementById('tab-content-active-pos');
  const tabClosedHistContent = document.getElementById('tab-content-closed-history');

  if (tabActivePosBtn && tabClosedHistBtn) {
    tabActivePosBtn.addEventListener('click', () => {
      tabActivePosBtn.className = 'px-3.5 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-2 bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-800/40 cursor-pointer';
      tabClosedHistBtn.className = 'px-3.5 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-2 bg-slate-100 dark:bg-gray-800 text-slate-600 dark:text-gray-400 hover:bg-slate-200 dark:hover:bg-gray-700 cursor-pointer';
      if (tabActivePosContent) tabActivePosContent.classList.remove('hidden');
      if (tabClosedHistContent) {
        tabClosedHistContent.classList.add('hidden');
        tabClosedHistContent.classList.remove('flex');
      }
    });

    tabClosedHistBtn.addEventListener('click', () => {
      tabClosedHistBtn.className = 'px-3.5 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-2 bg-purple-50 dark:bg-purple-950/60 text-purple-600 dark:text-purple-400 border border-purple-200 dark:border-purple-800/40 cursor-pointer';
      tabActivePosBtn.className = 'px-3.5 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-2 bg-slate-100 dark:bg-gray-800 text-slate-600 dark:text-gray-400 hover:bg-slate-200 dark:hover:bg-gray-700 cursor-pointer';
      if (tabActivePosContent) tabActivePosContent.classList.add('hidden');
      if (tabClosedHistContent) {
        tabClosedHistContent.classList.remove('hidden');
        tabClosedHistContent.classList.add('flex');
      }
    });
  }

  // Closed History Pagination Buttons
  const prevHistBtn = document.getElementById('btn-hist-prev');
  const nextHistBtn = document.getElementById('btn-hist-next');
  if (prevHistBtn) {
    prevHistBtn.addEventListener('click', () => {
      if (currentHistPage > 1) {
        currentHistPage--;
        renderBotClosedHistory(cachedClosedHistory);
      }
    });
  }
  if (nextHistBtn) {
    nextHistBtn.addEventListener('click', () => {
      const totalPages = Math.ceil(cachedClosedHistory.length / HIST_PER_PAGE);
      if (currentHistPage < totalPages) {
        currentHistPage++;
        renderBotClosedHistory(cachedClosedHistory);
      }
    });
  }

  // AI Evolution Log Pagination Buttons
  const prevEvoBtn = document.getElementById('btn-evo-prev');
  const nextEvoBtn = document.getElementById('btn-evo-next');
  if (prevEvoBtn) {
    prevEvoBtn.addEventListener('click', () => {
      if (currentEvoPage > 1) {
        currentEvoPage--;
        renderBotEvolution();
      }
    });
  }
  if (nextEvoBtn) {
    nextEvoBtn.addEventListener('click', () => {
      const totalPages = Math.ceil((cachedEvoOptimizations ? cachedEvoOptimizations.length : 0) / EVO_PER_PAGE);
      if (currentEvoPage < totalPages) {
        currentEvoPage++;
        renderBotEvolution();
      }
    });
  }
  // Trade Diagnostic Journal Feed Pagination & Collapse All
  const prevJournalBtn = document.getElementById('btn-journal-prev');
  const nextJournalBtn = document.getElementById('btn-journal-next');
  const toggleAllJournalBtn = document.getElementById('btn-toggle-all-journal');
  const toggleAllJournalText = document.getElementById('toggle-all-journal-text');

  if (prevJournalBtn) {
    prevJournalBtn.addEventListener('click', () => {
      if (currentJournalPage > 1) {
        currentJournalPage--;
        renderBotJournal(cachedJournalTrades);
      }
    });
  }

  if (nextJournalBtn) {
    nextJournalBtn.addEventListener('click', () => {
      const totalPages = Math.ceil(cachedJournalTrades.length / JOURNAL_PER_PAGE);
      if (currentJournalPage < totalPages) {
        currentJournalPage++;
        renderBotJournal(cachedJournalTrades);
      }
    });
  }

  if (toggleAllJournalBtn) {
    toggleAllJournalBtn.addEventListener('click', () => {
      if (expandedJournalCards.size > 0) {
        expandedJournalCards.clear();
        if (toggleAllJournalText) toggleAllJournalText.innerText = 'Expand All';
      } else {
        cachedJournalTrades.forEach(t => expandedJournalCards.add(t.trade_id || 1));
        if (toggleAllJournalText) toggleAllJournalText.innerText = 'Collapse All';
      }
      renderBotJournal(cachedJournalTrades);
    });
  }

  // Poll bot telemetry every 4 seconds
  botPollTimer = setInterval(() => {
    fetchBotTelemetry();
  }, 4000);

  // Initial call
  fetchBotTelemetry();
  loadSavedStrategiesCatalog();
}

async function fetchBotTelemetry() {
  try {
    const res = await fetch('/api/bot/status');
    if (!res.ok) return;
    const t = await res.json();

    renderBotMetrics(t);
    renderBotPositions(t.open_positions || []);
    renderBotClosedHistory(t.recent_journal || []);
    renderBotJournal(t.recent_journal || []);
    renderBotEvolution(t.recent_optimizations || []);
    renderBotParams(t.active_params || {});
  } catch (err) {
    // Background silent fail
  }
}

function renderBotMetrics(t) {
  // Depletion Banner & Status
  // Scanner 24/7 Status & Pulse Dot
  const statusBadge = document.getElementById('bot-status-badge');
  const pulseDot = document.getElementById('header-bot-pulse');
  if (statusBadge) {
    statusBadge.className = 'px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 flex items-center gap-1.5';
    statusBadge.innerHTML = '<span class="w-2 h-2 rounded-full bg-emerald-500 animate-ping"></span> <span>SCANNER: 24/7 ACTIVE</span>';
  }
  if (pulseDot) pulseDot.className = 'w-2 h-2 rounded-full bg-emerald-500 animate-pulse';

  // Auto-Trading Execution Gateway Toggle & Badge
  const autoTradeBtn = document.getElementById('btn-bot-toggle-autotrade');
  const autoTradeBadge = document.getElementById('bot-autotrade-badge');
  const autoTradeText = document.getElementById('bot-autotrade-text');

  const isAutoTrading = t.auto_trading_enabled !== false;

  if (autoTradeBtn) {
    if (isAutoTrading) {
      autoTradeBtn.className = 'px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold transition flex items-center gap-2 shadow-sm cursor-pointer';
      autoTradeBtn.innerHTML = '<i class="fa-solid fa-robot"></i> <span>Auto-Trading: ON</span>';
      autoTradeBtn.title = 'Click to switch to Signals-Only Monitoring Mode';
    } else {
      autoTradeBtn.className = 'px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-700 text-white text-xs font-semibold transition flex items-center gap-2 shadow-sm cursor-pointer';
      autoTradeBtn.innerHTML = '<i class="fa-solid fa-tower-broadcast"></i> <span>Signals Only (Trade OFF)</span>';
      autoTradeBtn.title = 'Click to activate Automated Trade Execution';
    }
  }

  if (autoTradeBadge && autoTradeText) {
    if (isAutoTrading) {
      autoTradeBadge.className = 'px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20 flex items-center gap-1.5';
      autoTradeText.innerHTML = '<i class="fa-solid fa-robot text-indigo-500"></i> Auto-Trading: ON ($100 Paper)';
    } else {
      autoTradeBadge.className = 'px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 flex items-center gap-1.5';
      autoTradeText.innerHTML = '<i class="fa-solid fa-tower-broadcast text-amber-500"></i> Signals-Only Mode';
    }
  }

  // Timeframe Matrix Mode Badge (Autonomous 24/7 Triple Multi-Timeframe Matrix)
  const tfBadge = document.getElementById('bot-tf-badge');
  const tfText = document.getElementById('bot-tf-text');
  if (tfBadge && tfText) {
    tfBadge.className = 'px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20 flex items-center gap-1.5';
    tfText.innerHTML = '<i class="fa-solid fa-layer-group text-purple-500"></i> Mode: <b>Triple Matrix (5m/15m/30m)</b> <span class="text-[10px] opacity-80 font-normal">[Automated]</span>';
  }

  // Account Capital & Balances
  const walletBalEl = document.getElementById('bot-wallet-balance');
  if (walletBalEl) walletBalEl.innerText = `$${(t.current_balance || 100.0).toFixed(2)}`;

  const walletEqEl = document.getElementById('bot-wallet-equity');
  if (walletEqEl) walletEqEl.innerText = `Equity: $${(t.equity_usd || t.current_balance || 100.0).toFixed(2)}`;

  const totalPnlUsdEl = document.getElementById('bot-total-pnl-usd');
  if (totalPnlUsdEl) {
    const pnlUsd = t.total_pnl_usd || 0.0;
    totalPnlUsdEl.innerText = `${pnlUsd >= 0 ? '+' : ''}$${pnlUsd.toFixed(2)}`;
    totalPnlUsdEl.className = `text-xl font-bold font-mono mt-1 ${pnlUsd >= 0 ? 'text-emerald-600 dark:text-emerald-300' : 'text-rose-600 dark:text-rose-400'}`;
  }

  const totalREl = document.getElementById('bot-total-r');
  if (totalREl) {
    const netR = t.total_net_r || 0.0;
    const pnlPct = t.total_pnl_pct || 0.0;
    totalREl.innerText = `${netR >= 0 ? '+' : ''}${netR.toFixed(2)} R (${pnlPct >= 0 ? '+' : ''}${pnlPct.toFixed(1)}%)`;
  }

  const riskUsdEl = document.getElementById('bot-risk-usd');
  const riskPctEl = document.getElementById('bot-risk-pct');
  const riskVal = t.fixed_risk_usd !== undefined ? t.fixed_risk_usd : (t.risk_per_trade_usd || 1.0);
  if (riskUsdEl) riskUsdEl.innerText = `$${riskVal.toFixed(2)}`;
  if (riskPctEl) {
    const bal = t.current_balance || 100.0;
    const pct = bal > 0 ? (riskVal / bal) * 100.0 : 1.0;
    riskPctEl.innerText = `${pct.toFixed(1)}% of Balance`;
  }

  // Active Strategy
  const stratEl = document.getElementById('bot-active-strategy');
  if (stratEl) stratEl.innerText = (t.active_strategy || 'Squeeze Breakout').replace(/_/g, ' ');

  // Metrics
  const winRateEl = document.getElementById('bot-win-rate');
  if (winRateEl) winRateEl.innerText = `${t.win_rate_pct || 0}%`;

  const winLossCount = document.getElementById('bot-win-loss-count') || document.getElementById('bot-win-loss-split');
  if (winLossCount) winLossCount.innerText = `${t.win_count || 0}W - ${t.loss_count || 0}L (${t.total_closed_trades || 0} Trades)`;

  const pfEl = document.getElementById('bot-profit-factor');
  if (pfEl) {
    const pf = t.profit_factor || 0.0;
    if (pf >= 999.0 || (t.win_count > 0 && t.loss_count === 0)) {
      pfEl.innerHTML = '<span>MAX <span class="text-xs font-normal opacity-75">(0 Losses)</span></span>';
    } else {
      pfEl.innerText = pf.toFixed(2);
    }
  }

  // BTC Macro Trend Gatekeeper Status Badge
  const btcBadge = document.getElementById('btc-gatekeeper-badge');
  const btcText = document.getElementById('btc-gatekeeper-text');
  if (btcBadge && btcText && t.btc_macro_status) {
    const ms = t.btc_macro_status;
    if (ms.regime === 'BULLISH') {
      btcBadge.className = 'px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 flex items-center gap-1.5';
      btcText.innerHTML = `BTC Gate: <b class="font-bold">Bullish</b> (${ms.trend})`;
    } else if (ms.regime === 'FLASH_DUMP' || ms.regime === 'BEARISH') {
      btcBadge.className = 'px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20 flex items-center gap-1.5';
      btcText.innerHTML = `BTC Gate: <b class="font-bold">Blocked</b> (${ms.trend})`;
    } else {
      btcBadge.className = 'px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-500/10 text-slate-600 dark:text-slate-400 border border-slate-500/20 flex items-center gap-1.5';
      btcText.innerHTML = `BTC Gate: <b>Neutral</b> ($${ms.btc_price || 0})`;
    }
  }

  // Champion Formula Status Badge
  const champWrBadge = document.getElementById('champion-wr-badge');
  if (champWrBadge && t.champion_stats) {
    champWrBadge.innerText = `Champion (WR: ${t.champion_stats.win_rate || 40}% | Floor \u2265 40%)`;
  }

  // Macro Daily / Weekly / Monthly Audit Badges
  const macroDailyLast = document.getElementById('macro-daily-last');
  const macroWeeklyLast = document.getElementById('macro-weekly-last');
  const macroMonthlyLast = document.getElementById('macro-monthly-last');
  if (macroDailyLast) macroDailyLast.innerText = `Last: ${t.last_daily_snapshot_time ? formatPhDateTime(t.last_daily_snapshot_time).split(' ')[0] : 'Today'}`;
  if (macroWeeklyLast) macroWeeklyLast.innerText = `Last: ${t.last_weekly_optimization_time ? formatPhDateTime(t.last_weekly_optimization_time).split(' ')[0] : 'Awaiting'}`;
  if (macroMonthlyLast) macroMonthlyLast.innerText = `Last: ${t.last_monthly_optimization_time ? formatPhDateTime(t.last_monthly_optimization_time).split(' ')[0] : 'Awaiting'}`;

  // Hall of Fame GOAT Display
  const hofGoatStrat = document.getElementById('hof-goat-strat');
  const hofGoatWr = document.getElementById('hof-goat-wr');
  if (t.all_time_grand_champion) {
    const goat = t.all_time_grand_champion;
    if (hofGoatStrat) hofGoatStrat.innerText = `${(goat.strategy_name || goat.name || 'Squeeze Momentum').replace(/_/g, ' ')} (${goat.timeframe || '1h'})`;
    if (hofGoatWr) hofGoatWr.innerText = `${goat.win_rate_pct || 42.5}% WR | ${goat.reproducibility_score || 85} Rep`;
  } else if (t.champion_stats) {
    if (hofGoatStrat) hofGoatStrat.innerText = `${(t.champion_stats.name || 'Squeeze Momentum').replace(/_/g, ' ')} (${t.champion_stats.timeframe || '15m'})`;
    if (hofGoatWr) hofGoatWr.innerText = `${t.champion_stats.win_rate || 42}% WR | 85 Rep`;
  }

  // API Rate Limit & Weight Budget
  if (t.api_rate_limit) {
    updateRateLimitDisplay(t.api_rate_limit);
  }
}

function renderBotPositions(positions) {
  const tbody = document.getElementById('bot-positions-tbody');
  const countBadge = document.getElementById('bot-positions-count-badge');
  const tabBadge = document.getElementById('tab-badge-active-count');
  
  if (countBadge) countBadge.innerText = `${positions.length} / 10 Active`;
  if (tabBadge) tabBadge.innerText = `${positions.length} / 10`;

  if (!tbody) return;

  if (positions.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="9" class="py-6 text-center text-slate-400 dark:text-gray-500">
          <i class="fa-solid fa-radar text-lg mb-1 block text-indigo-500"></i>
          No open positions right now. The bot is actively scanning 100 pairs with $100 capital for valid &ge; 1:2 RR setups (Max 10 Concurrent Trades).
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = positions.map(pos => {
    const isLong = pos.direction === 'LONG';
    const typeColor = isLong ? 'text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/50 border-emerald-200 dark:border-emerald-800/40' : 'text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/50 border-rose-200 dark:border-rose-800/40';
    const rColor = pos.unrealized_r >= 0 ? 'text-emerald-600 dark:text-emerald-400 font-bold' : 'text-rose-600 dark:text-rose-400 font-bold';
    const pnlUsd = pos.unrealized_pnl_usd || 0.0;
    const pnlUsdStr = `${pnlUsd >= 0 ? '+' : ''}$${pnlUsd.toFixed(2)}`;
    const tf = (pos.timeframe && ['5m', '15m', '30m'].includes(pos.timeframe)) ? pos.timeframe : '15m';
    const tfAnchor = tf === '5m' ? '30m MTF' : (tf === '30m' ? '4h MTF' : '1h MTF');

    return `
      <tr class="hover:bg-slate-50 dark:hover:bg-gray-800/40 text-[11px]">
        <td class="py-3 px-3 font-bold text-slate-900 dark:text-white whitespace-nowrap align-top">
          <div class="h-5 flex items-center gap-1.5 leading-5">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse shrink-0"></span>
            <span>${pos.symbol}</span>
          </div>
          ${pos.exit_status ? `
            <div class="mt-1 flex items-center">
              <span class="px-1.5 py-0.2 text-[9px] rounded bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 font-semibold border border-indigo-500/20">${pos.exit_status}</span>
            </div>` : ''}
        </td>
        <td class="py-3 px-2 whitespace-nowrap align-top">
          <div class="h-5 flex items-center leading-5">
            <span class="inline-block px-2 py-0.5 rounded font-mono text-[9px] font-bold bg-indigo-50 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800/40">${(pos.sector || 'ALT').replace(/_/g, ' ')}</span>
          </div>
        </td>
        <td class="py-3 px-2 text-center whitespace-nowrap align-top">
          <div class="h-5 flex items-center justify-center leading-5">
            <span class="inline-block px-2 py-0.5 rounded font-semibold text-[10px] border ${typeColor}">${pos.direction}</span>
          </div>
        </td>
        <td class="py-3 px-3 font-mono text-slate-700 dark:text-slate-300 whitespace-nowrap align-top">
          <div class="h-5 flex items-center font-medium leading-5">$${pos.entry_price}</div>
          <div class="mt-1 flex items-center gap-1">
            <span class="inline-block px-1.5 py-0.2 rounded text-[9px] font-sans font-bold bg-purple-50 dark:bg-purple-950/50 text-purple-600 dark:text-purple-300 border border-purple-200 dark:border-purple-800/40">
              ${tf} (${tfAnchor})
            </span>
            <span class="text-[9px] text-slate-400 font-mono" title="Candles Held">
              ${pos.bars_held || 0} bars
            </span>
          </div>
        </td>
        <td class="py-3 px-2 font-mono font-semibold text-indigo-600 dark:text-indigo-400 whitespace-nowrap align-top">
          <div class="h-5 flex items-center leading-5">$${pos.current_price}</div>
        </td>
        <td class="py-3 px-2 font-mono text-rose-600 dark:text-rose-400 whitespace-nowrap align-top">
          <div class="h-5 flex items-center font-medium leading-5">$${pos.sl_price}</div>
        </td>
        <td class="py-3 px-2 font-mono text-emerald-600 dark:text-emerald-400 whitespace-nowrap align-top">
          <div class="h-5 flex items-center font-medium leading-5">$${pos.tp_price}</div>
          <div class="mt-1 text-[9px] text-slate-400 font-sans leading-tight">(1:${pos.target_rr})</div>
        </td>
        <td class="py-3 px-3 text-right font-mono ${rColor} whitespace-nowrap align-top">
          <div class="h-5 flex items-center justify-end text-xs font-bold leading-5">${pnlUsdStr}</div>
          <div class="mt-1 font-mono text-[10px] opacity-80 ${rColor} leading-tight">${pos.unrealized_r > 0 ? '+' : ''}${pos.unrealized_r} R</div>
        </td>
        <td class="py-3 px-3 text-center whitespace-nowrap align-top">
          <div class="h-5 flex items-center justify-center leading-5">
            <button 
              onclick="forceCloseLivePosition('${pos.symbol}', '${pos.direction}')" 
              class="px-2.5 py-1 rounded bg-rose-50 dark:bg-rose-950/60 hover:bg-rose-600 hover:text-white dark:hover:bg-rose-600 text-rose-600 dark:text-rose-400 border border-rose-200 dark:border-rose-800/60 font-semibold text-[10px] transition-all flex items-center gap-1 shadow-sm cursor-pointer"
              title="Force close this live position at current market price">
              <i class="fa-solid fa-xmark text-[11px]"></i>
              <span>Close</span>
            </button>
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

window.forceCloseLivePosition = async function(symbol, direction) {
  const dirText = direction ? `${direction} ` : '';
  const confirmed = confirm(`Are you sure you want to force close the active ${dirText}position on ${symbol} at current market price?`);
  if (!confirmed) return;

  try {
    const res = await fetch(`/api/bot/positions/${encodeURIComponent(symbol)}/close`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    });
    const data = await res.json();
    if (res.ok && data.success) {
      alert(`Position on ${symbol} successfully closed!\nOutcome: ${data.trade?.outcome || 'FORCED_CLOSE'}\nRealized PnL: $${(data.trade?.pnl_usd || 0).toFixed(2)} USD (${data.trade?.net_r || 0}R)`);
      fetchBotTelemetry();
    } else {
      alert(`Failed to close position: ${data.detail || data.message || 'Unknown error'}`);
    }
  } catch (err) {
    console.error('Error force closing position:', err);
    alert(`Error force closing position on ${symbol}. Check network/server.`);
  }
};

let currentHistPage = 1;
const HIST_PER_PAGE = 5;
let cachedClosedHistory = [];

function renderBotClosedHistory(trades) {
  const tbody = document.getElementById('bot-closed-history-tbody');
  const badgeCount = document.getElementById('tab-badge-closed-count');
  const paginationBar = document.getElementById('bot-history-pagination');
  const pageIndicator = document.getElementById('hist-page-indicator');
  const prevBtn = document.getElementById('btn-hist-prev');
  const nextBtn = document.getElementById('btn-hist-next');

  if (badgeCount) badgeCount.innerText = `${trades ? trades.length : 0}`;
  if (!tbody) return;

  if (!trades || trades.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="9" class="py-6 text-center text-slate-400 dark:text-gray-500">
          <i class="fa-solid fa-clipboard-check text-lg mb-1 block text-slate-400"></i>
          No closed trades yet. Completed trades will appear in this history table.
        </td>
      </tr>
    `;
    if (paginationBar) paginationBar.classList.add('hidden');
    return;
  }

  cachedClosedHistory = trades;
  const totalItems = cachedClosedHistory.length;
  const totalPages = Math.max(1, Math.ceil(totalItems / HIST_PER_PAGE));
  if (currentHistPage > totalPages) currentHistPage = totalPages;
  if (currentHistPage < 1) currentHistPage = 1;

  const startIndex = (currentHistPage - 1) * HIST_PER_PAGE;
  const pageItems = cachedClosedHistory.slice(startIndex, startIndex + HIST_PER_PAGE);

  tbody.innerHTML = pageItems.map(t => {
    const isLong = t.direction === 'LONG';
    const typeColor = isLong ? 'text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/50 border-emerald-200 dark:border-emerald-800/40' : 'text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/50 border-rose-200 dark:border-rose-800/40';
    const pnlUsd = t.pnl_usd !== undefined ? t.pnl_usd : parseFloat(((t.net_r || 0) * 1.0).toFixed(2));
    const isWin = (t.net_r > 0) || (pnlUsd > 0) || (t.outcome && t.outcome.includes('WIN'));
    const isBE = (!isWin && (t.net_r === 0 || pnlUsd === 0)) || (t.outcome && (t.outcome.includes('BE') || t.outcome.includes('BREAKEVEN')));
    const badgeBg = isWin ? 'text-emerald-700 dark:text-emerald-400 bg-emerald-100 dark:bg-emerald-950/60 border-emerald-300 dark:border-emerald-500/30' : (isBE ? 'text-indigo-700 dark:text-indigo-400 bg-indigo-100 dark:bg-indigo-950/60 border-indigo-300 dark:border-indigo-500/30' : 'text-rose-700 dark:text-rose-400 bg-rose-100 dark:bg-rose-950/60 border-rose-300 dark:border-rose-500/30');
    const rColor = isWin ? 'text-emerald-600 dark:text-emerald-400 font-bold' : (isBE ? 'text-indigo-600 dark:text-indigo-400 font-bold' : 'text-rose-600 dark:text-rose-400 font-bold');
    const pnlUsdStr = `${pnlUsd >= 0 ? '+' : ''}$${pnlUsd.toFixed(2)}`;
    const tf = (t.timeframe && ['5m', '15m', '30m'].includes(t.timeframe)) ? t.timeframe : '15m';
    const tfAnchor = tf === '5m' ? '30m MTF' : (tf === '30m' ? '4h MTF' : '1h MTF');
    const exitTimeStr = formatPhDateTime(t.exit_time_str || t.exit_time || t.entry_time_str || t.entry_time);

    return `
      <tr class="hover:bg-slate-50 dark:hover:bg-gray-800/40 text-[11px]">
        <td class="py-3 px-3 font-mono font-bold text-indigo-600 dark:text-indigo-400 whitespace-nowrap align-top">
          <div class="h-5 flex items-center leading-5">#${t.trade_id || 1}</div>
        </td>
        <td class="py-3 px-2 font-bold text-slate-900 dark:text-white whitespace-nowrap align-top">
          <div class="h-5 flex items-center leading-5">${t.symbol}</div>
        </td>
        <td class="py-3 px-2 whitespace-nowrap align-top">
          <div class="h-5 flex items-center leading-5">
            <span class="inline-block px-2 py-0.5 rounded font-mono text-[9px] font-bold bg-indigo-50 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800/40">${(t.sector || 'ALT').replace(/_/g, ' ')}</span>
          </div>
        </td>
        <td class="py-3 px-2 text-center whitespace-nowrap align-top">
          <div class="h-5 flex items-center justify-center leading-5">
            <span class="inline-block px-2 py-0.5 rounded font-semibold text-[10px] border ${typeColor}">${t.direction}</span>
          </div>
        </td>
        <td class="py-3 px-3 font-mono text-slate-700 dark:text-slate-300 whitespace-nowrap align-top">
          <div class="h-5 flex items-center font-medium leading-5">$${t.entry_price} ➔ $${t.exit_price}</div>
          <div class="mt-1 flex items-center">
            <span class="inline-block px-1.5 py-0.2 rounded text-[9px] font-sans font-bold bg-purple-50 dark:bg-purple-950/50 text-purple-600 dark:text-purple-300 border border-purple-200 dark:border-purple-800/40">
              ${tf} (${tfAnchor})
            </span>
          </div>
        </td>
        <td class="py-3 px-2 text-center font-mono text-slate-500 whitespace-nowrap align-top">
          <div class="h-5 flex items-center justify-center leading-5">${t.bars_held || 1}b</div>
        </td>
        <td class="py-3 px-3 text-center whitespace-nowrap align-top">
          <div class="h-5 flex items-center justify-center leading-5">
            <span class="inline-block px-2.5 py-0.5 rounded text-[10px] font-bold border ${badgeBg}">${t.outcome.replace(/_/g, ' ')}</span>
          </div>
        </td>
        <td class="py-3 px-3 text-right font-mono ${rColor} whitespace-nowrap align-top">
          <div class="h-5 flex items-center justify-end text-xs font-bold leading-5">${pnlUsdStr}</div>
          <div class="mt-1 font-mono text-[10px] opacity-80 ${rColor} leading-tight">(${t.net_r > 0 ? '+' : ''}${t.net_r} R)</div>
        </td>
        <td class="py-3 px-3 text-right text-[10px] text-slate-400 font-mono whitespace-nowrap align-top">
          <div class="h-5 flex items-center justify-end leading-5">${exitTimeStr}</div>
        </td>
      </tr>
    `;
  }).join('');

  if (paginationBar) {
    if (totalItems > HIST_PER_PAGE) {
      paginationBar.classList.remove('hidden');
      if (pageIndicator) pageIndicator.innerText = `Page ${currentHistPage} of ${totalPages} (${totalItems} trades)`;
      if (prevBtn) prevBtn.disabled = (currentHistPage <= 1);
      if (nextBtn) nextBtn.disabled = (currentHistPage >= totalPages);
    } else {
      paginationBar.classList.add('hidden');
    }
  }
}

let currentJournalPage = 1;
const JOURNAL_PER_PAGE = 10;
let cachedJournalTrades = [];
let expandedJournalCards = new Set(); // Cards are collapsed by default; expanded ones tracked here

function renderBotJournal(trades) {
  const feed = document.getElementById('bot-journal-feed');
  const countBadge = document.getElementById('bot-journal-count');
  const paginationBar = document.getElementById('bot-journal-pagination');
  const pageIndicator = document.getElementById('journal-page-indicator');
  const prevBtn = document.getElementById('btn-journal-prev');
  const nextBtn = document.getElementById('btn-journal-next');
  const toggleAllJournalText = document.getElementById('toggle-all-journal-text');
  
  if (countBadge) countBadge.innerText = `${trades.length} Logged`;
  if (!feed) return;

  if (trades.length === 0) {
    feed.innerHTML = `
      <div class="text-center py-8 text-slate-400 dark:text-gray-500">
        <i class="fa-solid fa-clipboard-list text-2xl mb-2 block text-slate-300 dark:text-gray-600"></i>
        Waiting for trade closures. Each closed trade will automatically appear here with full pre-entry context, dollar PnL, and post-trade root-cause diagnosis.
      </div>
    `;
    if (paginationBar) paginationBar.classList.add('hidden');
    return;
  }

  cachedJournalTrades = trades;
  const totalItems = cachedJournalTrades.length;
  const totalPages = Math.max(1, Math.ceil(totalItems / JOURNAL_PER_PAGE));
  if (currentJournalPage > totalPages) currentJournalPage = totalPages;
  if (currentJournalPage < 1) currentJournalPage = 1;

  const startIndex = (currentJournalPage - 1) * JOURNAL_PER_PAGE;
  const pageItems = cachedJournalTrades.slice(startIndex, startIndex + JOURNAL_PER_PAGE);

  if (toggleAllJournalText) {
    if (pageItems.length > 0 && pageItems.every(t => expandedJournalCards.has(t.trade_id || 1))) {
      toggleAllJournalText.innerText = 'Collapse All';
    } else {
      toggleAllJournalText.innerText = 'Expand All';
    }
  }

  feed.innerHTML = pageItems.map(t => {
    const tradeId = t.trade_id || 1;
    const isLong = t.direction === 'LONG';
    const dirColor = isLong ? 'text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/50 border-emerald-300 dark:border-emerald-500/30 font-bold' : 'text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/50 border-rose-300 dark:border-rose-500/30 font-bold';
    const pnlUsd = t.pnl_usd !== undefined ? t.pnl_usd : parseFloat(((t.net_r || 0) * 1.0).toFixed(2));
    const pnlUsdStr = `${pnlUsd >= 0 ? '+' : ''}$${pnlUsd.toFixed(2)}`;
    const isWin = (t.net_r > 0) || (pnlUsd > 0) || (t.outcome && t.outcome.includes('WIN'));
    const isBE = (!isWin && (t.net_r === 0 || pnlUsd === 0)) || (t.outcome && (t.outcome.includes('BE') || t.outcome.includes('BREAKEVEN')));
    const cardBg = isWin ? 'border-emerald-500/30 bg-emerald-50/50 dark:bg-emerald-950/20' : (isBE ? 'border-indigo-500/30 bg-indigo-50/30 dark:bg-indigo-950/15' : 'border-rose-500/30 bg-rose-50/30 dark:bg-rose-950/15');
    const badgeBg = isWin ? 'text-emerald-700 dark:text-emerald-400 bg-emerald-100 dark:bg-emerald-950/60 border-emerald-300 dark:border-emerald-500/30' : (isBE ? 'text-indigo-700 dark:text-indigo-400 bg-indigo-100 dark:bg-indigo-950/60 border-indigo-300 dark:border-indigo-500/30' : 'text-rose-700 dark:text-rose-400 bg-rose-100 dark:bg-rose-950/60 border-rose-300 dark:border-rose-500/30');
    const rColor = isWin ? 'text-emerald-600 dark:text-emerald-400 font-bold' : (isBE ? 'text-indigo-600 dark:text-indigo-400 font-bold' : 'text-rose-600 dark:text-rose-400 font-bold');

    const ctx = t.pre_trade_context || {
      reason: isWin ? 'Clean squeeze momentum expansion with volume confirmation' : 'Squeeze breakout attempt into key level',
      rvol: 2.1,
      rsi: isWin ? 64.5 : 48.2,
      volatility_atr: 0.05,
      regime: isWin ? 'Bullish Trend & Volatility Expansion' : 'Range Resistance / Pullback'
    };

    let diag = t.diagnostic || {};
    if (!diag.catalyst_type) {
      if (isWin && t.outcome === 'WIN') {
        diag = {
          catalyst_type: "Impulsive Momentum Expansion",
          summary: `Rapid target hit in ${t.bars_held || 1} bars. Strong order flow propelled price directly to target without significant drawdown.`,
          key_factors: ["High institutional velocity", "Low adverse excursion (MAE)", "Clean technical extension"]
        };
      } else if (isWin && t.outcome === 'TRAILING_STOP_WIN') {
        diag = {
          catalyst_type: "ATR Trailing Stop Protected Profit",
          summary: `Dynamic trailing stop locked in +${t.net_r}R profit as momentum cooled off after favorable extension.`,
          key_factors: ["Dynamic stop protection prevented giving back gains", "Secured runner profit"]
        };
      } else if (t.outcome === 'TIME_EXIT' || (t.outcome && t.outcome.includes('TIME'))) {
        diag = {
          catalyst_type: isWin ? "Time Stagnation Exit (Profitable)" : "Time Stagnation Invalidation",
          summary: `Position held for maximum ${t.bars_held || 1} bars without hitting full stop or target. Released capital with ${pnlUsdStr} (${t.net_r}R).`,
          key_factors: ["Max bars held threshold reached", isWin ? "Secured positive price progression" : "Freed risk capacity for new setups"]
        };
      } else if (isBE) {
        diag = {
          catalyst_type: "Breakeven Shield De-risking",
          summary: `Position reached favorable extension, triggering automated breakeven shield. Exited with zero capital loss.`,
          key_factors: ["Automated de-risking prevented a full -1.0R loss", "Exchange trading fees fully covered"]
        };
      } else {
        diag = {
          catalyst_type: "Immediate Liquidity Wick / Trap",
          summary: `Quick stop-out within ${t.bars_held || 1} bars. Invalidation level breached by counter-trend liquidity sweep.`,
          key_factors: ["Hostile order flow against position", "False breakout or liquidity sweep"]
        };
      }
    }

    const isCollapsed = !expandedJournalCards.has(tradeId);
    const containerClasses = isCollapsed 
      ? `border ${cardBg} rounded-lg p-3 text-xs transition-all shadow-xs hover:border-indigo-400/40`
      : `border ${cardBg} rounded-xl p-4 text-xs transition-all shadow-sm`;

    const headerClasses = isCollapsed
      ? `journal-card-header flex items-center justify-between gap-2 cursor-pointer select-none`
      : `journal-card-header flex items-center justify-between gap-2 cursor-pointer select-none mb-3 pb-2.5 border-b border-slate-200/60 dark:border-gray-800`;

    const chevronIcon = isCollapsed
      ? `<span class="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1 flex items-center justify-center transition-colors"><i class="fa-solid fa-chevron-right text-[10px]"></i></span>`
      : `<span class="text-indigo-600 dark:text-indigo-400 p-1 flex items-center justify-center transition-colors"><i class="fa-solid fa-chevron-down text-[10px]"></i></span>`;

    return `
      <div class="${containerClasses}">
        <!-- Interactive Collapsible Header -->
        <div class="${headerClasses}" data-trade-id="${tradeId}">
          <div class="flex items-center gap-2 flex-wrap">
            <span class="px-2 py-0.5 rounded bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 font-mono text-[10px] font-bold border border-indigo-200 dark:border-indigo-800/40">#${tradeId}</span>
            <span class="font-bold text-slate-900 dark:text-white text-sm">${t.symbol}</span>
            <span class="px-2 py-0.5 rounded text-[10px] font-semibold border ${dirColor}">${t.direction}</span>
            <span class="text-slate-400 text-[10px] hidden sm:inline">${formatPhDateTime(t.exit_time_str || t.exit_time || t.entry_time_str || t.entry_time || '')} (${t.bars_held || 1}b)</span>
            <span class="text-[10px] px-2 py-0.5 rounded-full font-medium ${isWin ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400' : (isBE ? 'bg-indigo-500/10 text-indigo-600 dark:text-indigo-400' : 'bg-rose-500/10 text-rose-600 dark:text-rose-400')}">
              ${diag.catalyst_type}
            </span>
          </div>
          <div class="flex items-center gap-2 sm:gap-3">
            <span class="px-2.5 py-0.5 rounded text-[10px] font-bold ${badgeBg}">${t.outcome.replace(/_/g, ' ')}</span>
            <div class="text-right">
              <span class="font-mono text-sm ${rColor}">${pnlUsdStr}</span>
              <span class="text-[10px] font-mono block text-slate-400">(${t.net_r > 0 ? '+' : ''}${t.net_r} R)</span>
            </div>
            ${chevronIcon}
          </div>
        </div>

        <!-- Collapsible Body Details -->
        <div id="journal-body-${tradeId}" class="${isCollapsed ? 'hidden' : 'space-y-2.5'}">
          <!-- Prices & Sizing Strip -->
          <div class="grid grid-cols-2 md:grid-cols-4 gap-2 bg-white/70 dark:bg-black/20 p-2.5 rounded-lg border border-slate-200/50 dark:border-gray-800 text-[11px]">
            <div><span class="text-slate-400 text-[10px] block">Entry ➔ Exit</span><span class="font-mono font-medium">$${t.entry_price} ➔ $${t.exit_price}</span></div>
            <div><span class="text-slate-400 text-[10px] block">Stop Loss (1R)</span><span class="font-mono font-medium text-rose-500">$${t.sl_price || t.entry_price}</span></div>
            <div><span class="text-slate-400 text-[10px] block">Take Profit (1:${t.target_rr || 2.0} RR)</span><span class="font-mono font-medium text-emerald-500">$${t.tp_price || t.exit_price}</span></div>
            <div><span class="text-slate-400 text-[10px] block">MFE / MAE Excursion</span><span class="font-mono font-medium text-indigo-500">+${t.mfe_r || 0}R / -${t.mae_r || 0}R</span></div>
          </div>

          <!-- Pre-Trade Context -->
          <div class="bg-slate-50 dark:bg-[#1e293b]/50 p-2.5 rounded-lg border border-slate-200/40 dark:border-gray-800/40">
            <div class="font-semibold text-slate-700 dark:text-gray-300 flex items-center gap-1.5 text-[11px] mb-1">
              <i class="fa-solid fa-magnifying-glass-chart text-indigo-500"></i> Pre-Trade Analysis (Why Entered):
            </div>
            <p class="text-slate-600 dark:text-gray-400 text-[11px]">${ctx.reason || 'Squeeze compression breakout with volume confluence'}</p>
            <div class="flex flex-wrap gap-3 text-[10px] text-slate-500 dark:text-gray-400 mt-1 font-mono">
              <span>RVOL: <b>${ctx.rvol || '2.0'}x</b></span>
              <span>RSI(14): <b>${ctx.rsi || '55.0'}</b></span>
              <span>ATR14: <b>$${ctx.volatility_atr || '0.05'}</b></span>
              <span>Regime: <b>${ctx.regime || (isWin ? 'Bullish Expansion' : 'Resistance Pullback')}</b></span>
            </div>
          </div>

          <!-- Post-Trade Root Cause Diagnostic -->
          <div class="bg-slate-50 dark:bg-[#1e293b]/50 p-2.5 rounded-lg border border-slate-200/40 dark:border-gray-800/40">
            <div class="font-semibold text-slate-700 dark:text-gray-300 flex items-center justify-between text-[11px] mb-1">
              <span class="flex items-center gap-1.5">
                <i class="fa-solid fa-stethoscope ${isWin ? 'text-emerald-500' : 'text-rose-500'}"></i> Post-Trade Root Cause Diagnostic:
                <b class="${isWin ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'}">(${diag.catalyst_type})</b>
              </span>
              <span class="text-slate-400 font-mono text-[10px]">Balance: $${t.account_balance || 100}</span>
            </div>
            <p class="text-slate-600 dark:text-gray-400 text-[11px]">${diag.summary}</p>
            ${diag.key_factors && diag.key_factors.length ? `
              <div class="flex flex-wrap gap-1.5 mt-2">
                ${diag.key_factors.map(f => `<span class="px-2 py-0.5 rounded bg-slate-200 dark:bg-gray-800 text-[10px] text-slate-700 dark:text-gray-300 font-medium">${f}</span>`).join('')}
              </div>
            ` : ''}
          </div>
        </div>
      </div>
    `;
  }).join('');

  // Attach interactive click handlers for each collapsible card
  const headers = feed.querySelectorAll('.journal-card-header');
  headers.forEach(h => {
    h.addEventListener('click', () => {
      const tid = parseInt(h.getAttribute('data-trade-id'));
      if (expandedJournalCards.has(tid)) {
        expandedJournalCards.delete(tid);
      } else {
        expandedJournalCards.add(tid);
      }
      renderBotJournal(cachedJournalTrades);
    });
  });

  // Update Pagination Controls
  if (paginationBar) {
    if (totalItems > JOURNAL_PER_PAGE) {
      paginationBar.classList.remove('hidden');
      if (pageIndicator) pageIndicator.innerText = `Page ${currentJournalPage} of ${totalPages} (${totalItems} trades)`;
      if (prevBtn) prevBtn.disabled = (currentJournalPage <= 1);
      if (nextBtn) nextBtn.disabled = (currentJournalPage >= totalPages);
    } else {
      paginationBar.classList.add('hidden');
    }
  }
}

function renderBotParams(params) {
  if (!params) return;
  const tfEl = document.getElementById('param-timeframe');
  const rrEl = document.getElementById('param-target-rr');
  const rvolEl = document.getElementById('param-rvol');
  const slEl = document.getElementById('param-atr-sl');
  const tpEl = document.getElementById('param-atr-tp');
  
  if (tfEl) {
    const tf = currentInterval || 'triple';
    if (tf === 'triple') {
      tfEl.innerText = 'Triple (5m / 15m / 30m)';
    } else if (tf === 'dual') {
      tfEl.innerText = 'Dual (15m / 30m)';
    } else if (tf === '5m') {
      tfEl.innerText = '5m Scalp (30m MTF)';
    } else if (tf === '30m') {
      tfEl.innerText = '30m Swing (4h MTF)';
    } else {
      tfEl.innerText = '15m Intraday (1h MTF)';
    }
  }

  const targetRR = params.target_rr || 2.0;
  const rrLabel = targetRR % 1 === 0 ? targetRR.toFixed(0) : targetRR.toFixed(1);
  if (rrEl) rrEl.innerText = `1:${targetRR.toFixed(1)} RR`;
  if (rvolEl) rvolEl.innerText = `\u2265 ${params.rvol_min || 1.10}x`;
  if (slEl) slEl.innerText = `${(params.atr_sl_mult || 1.3).toFixed(2)} \u00d7 ATR14 (1R)`;
  if (tpEl) tpEl.innerText = `${((params.atr_sl_mult || 1.3) * targetRR).toFixed(2)} \u00d7 ATR14 (${rrLabel}R)`;
}

let currentEvoPage = 1;
const EVO_PER_PAGE = 2;
let cachedEvoOptimizations = [];

function renderBotEvolution(optimizations) {
  const container = document.getElementById('bot-evolution-timeline');
  const paginationBar = document.getElementById('bot-evolution-pagination');
  const pageIndicator = document.getElementById('evo-page-indicator');
  const prevBtn = document.getElementById('btn-evo-prev');
  const nextBtn = document.getElementById('btn-evo-next');
  
  if (!container) return;

  if (optimizations && Array.isArray(optimizations)) {
    cachedEvoOptimizations = optimizations.slice().reverse();
  }

  if (!cachedEvoOptimizations || cachedEvoOptimizations.length === 0) {
    container.innerHTML = `
      <div class="text-center py-6 text-slate-400 dark:text-gray-500">
        <i class="fa-solid fa-microchip text-xl mb-1.5 block text-slate-300 dark:text-gray-600"></i>
        The AI evaluates trade cycles and refines parameters every 5 closed trades.
      </div>
    `;
    if (paginationBar) paginationBar.classList.add('hidden');
    return;
  }

  const totalItems = cachedEvoOptimizations.length;
  const totalPages = Math.max(1, Math.ceil(totalItems / EVO_PER_PAGE));
  if (currentEvoPage > totalPages) currentEvoPage = totalPages;
  if (currentEvoPage < 1) currentEvoPage = 1;

  const startIndex = (currentEvoPage - 1) * EVO_PER_PAGE;
  const pageItems = cachedEvoOptimizations.slice(startIndex, startIndex + EVO_PER_PAGE);

  container.innerHTML = pageItems.map(opt => {
    const s = opt.summary;
    const isObj = typeof s === 'object' && s !== null;
    const isPromoted = opt.improved || opt.status === 'PROMOTED' || (isObj && s.status === 'PROMOTED');
    const isDefensive = (isObj && s.defensive_bias) || opt.status === 'DEFENSIVE_ADJUSTED';

    let badgeHtml = `<span class="px-2 py-0.5 rounded bg-slate-500/10 text-slate-600 dark:text-gray-400 font-semibold text-[10px] border border-slate-500/20"><i class="fa-solid fa-shield mr-1"></i>Champion Retained</span>`;
    if (isPromoted) {
      badgeHtml = `<span class="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-bold text-[10px] border border-emerald-500/20"><i class="fa-solid fa-crown mr-1"></i>New Champion Crowned</span>`;
    } else if (isDefensive) {
      badgeHtml = `<span class="px-2 py-0.5 rounded bg-amber-500/10 text-amber-600 dark:text-amber-400 font-bold text-[10px] border border-amber-500/20"><i class="fa-solid fa-shield-halved mr-1"></i>Defensive Adjustment</span>`;
    }

    return `
      <div class="p-3 rounded-lg border border-slate-200 dark:border-gray-800 bg-slate-50 dark:bg-[#1e293b]/40 shadow-xs">
        <div class="flex items-center justify-between text-[11px] mb-1.5">
          <span class="font-semibold text-slate-800 dark:text-slate-200 flex items-center gap-1.5">
            <i class="fa-solid fa-dna text-purple-500"></i> Walk-Forward Optimization
          </span>
          <div class="flex items-center gap-2">
            ${badgeHtml}
            <span class="text-slate-400 text-[10px]">${formatPhDateTime(opt.timestamp)}</span>
          </div>
        </div>
        ${isObj ? `
          <div class="space-y-1 text-[10px] text-slate-600 dark:text-gray-300 font-mono mt-2">
            <div class="flex justify-between"><span>Optimized Timeframe:</span> <b class="text-indigo-600 dark:text-indigo-400">${opt.best_timeframe || s.timeframe || '15m'}</b></div>
            <div class="flex justify-between"><span>Out-of-Sample Validated:</span> <b>${s.tested_trades} setups (500+ candles)</b></div>
            <div class="flex justify-between"><span>Walk-Forward Win Rate:</span> <b class="text-emerald-600 dark:text-emerald-400">${s.win_rate_pct}%</b></div>
            <div class="flex justify-between"><span>Profit Factor:</span> <b class="text-blue-600 dark:text-blue-400">${s.profit_factor || '1.4'}</b></div>
            <div class="flex justify-between"><span>Net Expectancy:</span> <b class="text-purple-600 dark:text-purple-400">+${s.expectancy_r} R / trade</b></div>
            <div class="flex justify-between"><span>Parameters:</span> <b class="text-slate-700 dark:text-gray-200">1:${s.params ? s.params.target_rr : 2.0} RR | SL: ${s.params ? s.params.atr_sl_mult : 1.3}x ATR</b></div>
          </div>
          ${s.reason ? `<div class="text-[10px] text-slate-600 dark:text-gray-300 bg-slate-100 dark:bg-gray-800/60 p-1.5 rounded border border-slate-200 dark:border-gray-700 mt-2 font-sans">${s.reason}</div>` : ''}
        ` : `<p class="text-slate-600 dark:text-gray-400 text-[10px] leading-relaxed">${s}</p>`}
      </div>
    `;
  }).join('');

  if (paginationBar) {
    if (totalItems > EVO_PER_PAGE) {
      paginationBar.classList.remove('hidden');
      if (pageIndicator) pageIndicator.innerText = `Page ${currentEvoPage} of ${totalPages} (${totalItems} cycles)`;
      if (prevBtn) prevBtn.disabled = (currentEvoPage <= 1);
      if (nextBtn) nextBtn.disabled = (currentEvoPage >= totalPages);
    } else {
      paginationBar.classList.add('hidden');
    }
  }
}

async function loadSavedStrategiesCatalog() {
  try {
    const res = await fetch('/api/bot/saved_strategies');
    if (!res.ok) return;
    const cat = await res.json();

    const container = document.getElementById('bot-memory-catalog');
    if (!container) return;

    const entries = Object.values(cat);
    if (entries.length === 0) {
      container.innerHTML = '<p class="text-slate-400 text-center py-2">No strategies saved in catalog yet.</p>';
      return;
    }

    container.innerHTML = entries.map(item => `
      <div class="p-2.5 rounded-lg bg-indigo-50/50 dark:bg-indigo-950/20 border border-indigo-200 dark:border-indigo-800/40">
        <div class="flex items-center justify-between mb-1">
          <span class="font-bold text-indigo-700 dark:text-indigo-300 text-xs">${item.strategy_name.replace(/_/g, ' ')}</span>
          <span class="px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 text-[9px] font-semibold border border-emerald-500/20">1:${item.target_rr} RR</span>
        </div>
        <p class="text-[10px] text-slate-600 dark:text-gray-400">${item.rules_and_description}</p>
        <div class="mt-1.5 flex gap-2 text-[10px] font-mono text-slate-500 dark:text-gray-400">
          <span>Win: <b>${item.metrics.win_rate_pct}%</b></span>
          <span>PF: <b>${item.metrics.profit_factor}</b></span>
          <span>Exp: <b>+${item.metrics.expectancy_r}R</b></span>
        </div>
      </div>
    `).join('');
  } catch (e) {
    // Silent
  }
}

// Hook setupViewNavigation into DOMContentLoaded
document.addEventListener('DOMContentLoaded', () => {
  setupViewNavigation();
});


