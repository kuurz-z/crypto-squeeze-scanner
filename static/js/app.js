// Application State
let currentInterval = '1h';
let currentSymbol = 'BTCUSDT';
let currentFilter = 'all'; // 'all' | 'signals' | 'squeeze'
let searchQuery = '';
let scannerData = [];
let autoRefreshTimer = null;

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initCharts();
  setupEventListeners();
  
  // Initial load
  fetchScan();
  loadSymbolChart(currentSymbol);
  
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
  // Timeframe buttons
  document.querySelectorAll('.tf-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      document.querySelectorAll('.tf-btn').forEach(b => {
        b.classList.remove('bg-indigo-600', 'text-white', 'shadow');
        b.classList.add('text-slate-600', 'dark:text-gray-400');
      });
      btn.classList.add('bg-indigo-600', 'text-white', 'shadow');
      btn.classList.remove('text-slate-600', 'dark:text-gray-400');
      
      currentInterval = btn.dataset.tf;
      fetchScan(true);
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

  // Refresh button
  const refreshBtn = document.getElementById('btn-refresh');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => {
      fetchScan(true);
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
    html += `<option value="${sym}" ${isSel}>${sym}</option>`;
  });
  
  btSelect.innerHTML = html;
  btSelect.value = currentVal;
}

async function fetchScan(showSpinner = true) {
  const tbody = document.getElementById('scanner-tbody');
  if (showSpinner && tbody && scannerData.length === 0) {
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
    const res = await fetch(`/api/scan?interval=${currentInterval}&limit=60`);
    if (!res.ok) throw new Error('Scan failed');
    const json = await res.json();
    scannerData = json.data || [];
    renderScannerTable();
    updateBacktestDropdown(scannerData);
  } catch (err) {
    console.error('Scan error:', err);
    if (tbody && scannerData.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" class="py-6 text-center text-rose-500">Failed to fetch live scan data.</td></tr>`;
    }
  }
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
    }
    return true;
  });

  if (badge) badge.innerText = `${filtered.length} Pairs`;

  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" class="py-6 text-center text-slate-400 dark:text-gray-500">No coins match the filter.</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.map(item => {
    const isSelected = item.symbol === currentSymbol ? 'selected-row' : '';
    const formattedPrice = item.price < 1 ? item.price.toFixed(5) : item.price.toFixed(2);
    
    // Squeeze badge
    let squeezeHtml = '';
    if (item.is_squeeze) {
      squeezeHtml = `<span class="px-2 py-0.5 rounded text-[10px] bg-amber-500/15 dark:bg-amber-500/10 text-amber-700 dark:text-amber-300 border border-amber-400/40 dark:border-amber-500/30 font-medium inline-flex items-center gap-1"><i class="fa-solid fa-compress text-[9px]"></i> ${item.squeeze_bars} bars</span>`;
    } else {
      squeezeHtml = `<span class="text-[10px] text-slate-400 dark:text-gray-600">--</span>`;
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
        <td class="py-2.5 px-3 font-semibold text-slate-900 dark:text-white flex items-center gap-1.5">
          <i class="fa-brands fa-bitcoin text-indigo-600 dark:text-indigo-400 text-xs"></i>
          ${item.symbol.replace('USDT', '')}<span class="text-[10px] text-slate-400 dark:text-gray-500 font-normal">/USDT</span>
        </td>
        <td class="py-2.5 px-2 font-mono font-medium text-slate-800 dark:text-gray-200">$${formattedPrice}</td>
        <td class="py-2.5 px-2 text-center">${squeezeHtml}</td>
        <td class="py-2.5 px-2 text-center">${signalHtml}</td>
        <td class="py-2.5 px-2 text-right ${trendColor} text-[11px] font-medium">
          <i class="fa-solid ${trendIcon} text-[10px]"></i> ${item.pct_from_ema200 > 0 ? '+' : ''}${item.pct_from_ema200}%
        </td>
      </tr>
    `;
  }).join('');
}

function onSelectCoin(symbol) {
  currentSymbol = symbol;
  renderScannerTable();
  loadSymbolChart(symbol);
  
  // Sync backtest select dropdown
  const btSelect = document.getElementById('bt-symbol');
  if (btSelect && symbol !== 'ALL') {
    btSelect.value = symbol;
  }
}

async function loadSymbolChart(symbol) {
  try {
    const res = await fetch(`/api/candles/${symbol}?interval=${currentInterval}&limit=300`);
    if (!res.ok) throw new Error('Failed to load chart');
    const data = await res.json();
    
    updateChartData(data);
    updateTopMetrics(data);
  } catch (err) {
    console.error('Error loading chart:', err);
  }
}

function updateTopMetrics(data) {
  const m = data.current_metrics;
  if (!m) return;

  document.getElementById('active-symbol-badge').innerText = data.symbol;
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
            <td class="py-1.5 px-3 text-slate-500 dark:text-gray-400">${symPrefix}#${t.trade_num}</td>
            <td class="py-1.5 px-3 font-semibold ${t.direction === 'LONG' ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'}">${t.direction}</td>
            <td class="py-1.5 px-3 font-mono text-slate-800 dark:text-slate-200">$${t.entry_price}</td>
            <td class="py-1.5 px-3 font-mono text-rose-600 dark:text-rose-300">$${t.sl_price}</td>
            <td class="py-1.5 px-3 font-mono text-emerald-600 dark:text-emerald-300">$${t.tp_target_price}</td>
            <td class="py-1.5 px-3 font-mono text-slate-800 dark:text-slate-200">$${t.exit_price}</td>
            <td class="py-1.5 px-3 text-center">
              <span class="px-2 py-0.5 rounded border text-[10px] font-semibold ${badgeColor}">${t.outcome}</span>
            </td>
            <td class="py-1.5 px-3 text-right font-mono ${rColor}">${t.net_r > 0 ? '+' : ''}${t.net_r}R</td>
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

  if (scannerBtn && botBtn) {
    scannerBtn.addEventListener('click', () => {
      currentView = 'scanner';
      scannerView.classList.remove('hidden');
      botView.classList.add('hidden');

      scannerBtn.className = 'px-3 py-1.5 rounded-md transition bg-indigo-600 text-white shadow flex items-center gap-1.5';
      botBtn.className = 'px-3 py-1.5 rounded-md transition text-slate-600 dark:text-gray-400 hover:text-slate-900 dark:hover:text-white flex items-center gap-1.5';
    });

    botBtn.addEventListener('click', () => {
      currentView = 'bot';
      scannerView.classList.add('hidden');
      botView.classList.remove('hidden');

      botBtn.className = 'px-3 py-1.5 rounded-md transition bg-indigo-600 text-white shadow flex items-center gap-1.5';
      scannerBtn.className = 'px-3 py-1.5 rounded-md transition text-slate-600 dark:text-gray-400 hover:text-slate-900 dark:hover:text-white flex items-center gap-1.5';

      fetchBotTelemetry();
    });
  }

  // Bot action buttons
  const resetBtn = document.getElementById('btn-bot-reset-balance');
  if (resetBtn) {
    resetBtn.addEventListener('click', async () => {
      if (confirm('Reset paper wallet balance to $100.00 USD and clear trade history?')) {
        try {
          const res = await fetch('/api/bot/reset', { method: 'POST' });
          const data = await res.json();
          alert('Account balance reset to $100.00 USD!');
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
  if (resetBtn) resetBtn.addEventListener('click', openFundModal);
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
        renderBotEvolution(cachedEvoOptimizations.slice().reverse());
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
      isAllJournalCollapsed = !isAllJournalCollapsed;
      if (isAllJournalCollapsed) {
        cachedJournalTrades.forEach(t => collapsedJournalCards.add(t.trade_id || 1));
        if (toggleAllJournalText) toggleAllJournalText.innerText = 'Expand All';
      } else {
        collapsedJournalCards.clear();
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
  if (macroDailyLast) macroDailyLast.innerText = `Last: ${t.last_daily_snapshot_time ? t.last_daily_snapshot_time.split(' ')[0] : 'Today'}`;
  if (macroWeeklyLast) macroWeeklyLast.innerText = `Last: ${t.last_weekly_optimization_time ? t.last_weekly_optimization_time.split(' ')[0] : 'Awaiting'}`;
  if (macroMonthlyLast) macroMonthlyLast.innerText = `Last: ${t.last_monthly_optimization_time ? t.last_monthly_optimization_time.split(' ')[0] : 'Awaiting'}`;

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
        <td colspan="8" class="py-6 text-center text-slate-400 dark:text-gray-500">
          <i class="fa-solid fa-radar text-lg mb-1 block text-indigo-500"></i>
          No open positions right now. The bot is actively scanning 100 pairs with $100 capital for valid &ge; 1:2 RR setups (Max 10 Concurrent Trades).
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = positions.map(pos => {
    const isLong = pos.direction === 'LONG';
    const typeColor = isLong ? 'text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/50' : 'text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/50';
    const rColor = pos.unrealized_r >= 0 ? 'text-emerald-600 dark:text-emerald-400 font-bold' : 'text-rose-600 dark:text-rose-400 font-bold';
    const pnlUsd = pos.unrealized_pnl_usd || 0.0;
    const pnlUsdStr = `${pnlUsd >= 0 ? '+' : ''}$${pnlUsd.toFixed(2)}`;
    const tf = pos.timeframe || pos.pre_trade_context?.timeframe || '15m';

    return `
      <tr class="hover:bg-slate-50 dark:hover:bg-gray-800/40 text-[11px]">
        <td class="py-2 px-2.5 font-bold text-slate-900 dark:text-white flex items-center gap-1.5 whitespace-nowrap">
          <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
          ${pos.symbol}
          ${pos.exit_status ? `<span class="px-1.5 py-0.5 text-[9px] rounded bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 font-semibold border border-indigo-500/20">${pos.exit_status}</span>` : ''}
        </td>
        <td class="py-2 px-1.5 whitespace-nowrap">
          <span class="px-1.5 py-0.5 rounded font-mono text-[9px] font-bold bg-indigo-50 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800/40">${(pos.sector || 'ALT').replace(/_/g, ' ')}</span>
        </td>
        <td class="py-2 px-1.5 whitespace-nowrap">
          <span class="px-2 py-0.5 rounded font-semibold text-[10px] border ${typeColor}">${pos.direction}</span>
        </td>
        <td class="py-2 px-1.5 font-mono text-slate-700 dark:text-slate-300 whitespace-nowrap">
          <div class="font-medium">$${pos.entry_price}</div>
          <span class="inline-block px-1.5 py-0.2 rounded text-[9px] font-sans font-bold bg-purple-50 dark:bg-purple-950/50 text-purple-600 dark:text-purple-300 border border-purple-200 dark:border-purple-800/40">
            ${tf} TF
          </span>
        </td>
        <td class="py-2 px-1.5 font-mono font-semibold text-indigo-600 dark:text-indigo-400 whitespace-nowrap">$${pos.current_price}</td>
        <td class="py-2 px-1.5 font-mono text-rose-600 dark:text-rose-400 whitespace-nowrap">$${pos.sl_price}</td>
        <td class="py-2 px-1.5 font-mono text-emerald-600 dark:text-emerald-400 whitespace-nowrap">
          <div>$${pos.tp_price}</div>
          <span class="text-[9px] text-slate-400 font-sans">(1:${pos.target_rr})</span>
        </td>
        <td class="py-2 px-2.5 text-right font-mono ${rColor} whitespace-nowrap">
          <div class="text-xs">${pnlUsdStr}</div>
          <div class="text-[10px] opacity-80">${pos.unrealized_r > 0 ? '+' : ''}${pos.unrealized_r} R</div>
        </td>
      </tr>
    `;
  }).join('');
}

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
    const typeColor = isLong ? 'text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/50' : 'text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/50';
    const isWin = t.outcome === 'WIN' || t.outcome === 'TRAILING_STOP_WIN';
    const isBE = t.outcome === 'BE_EXIT' || t.outcome === 'BREAKEVEN_DEFENSE';
    const badgeBg = isWin ? 'text-emerald-700 dark:text-emerald-400 bg-emerald-100 dark:bg-emerald-950/60 border-emerald-300 dark:border-emerald-500/30' : (isBE ? 'text-indigo-700 dark:text-indigo-400 bg-indigo-100 dark:bg-indigo-950/60 border-indigo-300 dark:border-indigo-500/30' : 'text-rose-700 dark:text-rose-400 bg-rose-100 dark:bg-rose-950/60 border-rose-300 dark:border-rose-500/30');
    const rColor = t.net_r > 0 ? 'text-emerald-600 dark:text-emerald-400 font-bold' : (t.net_r === 0 ? 'text-indigo-600 dark:text-indigo-400 font-bold' : 'text-rose-600 dark:text-rose-400 font-bold');
    const pnlUsd = t.pnl_usd !== undefined ? t.pnl_usd : round(t.net_r * 1.0, 2);
    const pnlUsdStr = `${pnlUsd >= 0 ? '+' : ''}$${pnlUsd.toFixed(2)}`;
    const tf = t.timeframe || t.pre_trade_context?.timeframe || '15m';

    return `
      <tr class="hover:bg-slate-50 dark:hover:bg-gray-800/40 text-[11px]">
        <td class="py-2 px-2 font-mono font-bold text-indigo-600 dark:text-indigo-400 whitespace-nowrap">#${t.trade_id || 1}</td>
        <td class="py-2 px-1.5 font-bold text-slate-900 dark:text-white whitespace-nowrap">${t.symbol}</td>
        <td class="py-2 px-1.5 whitespace-nowrap">
          <span class="px-1.5 py-0.5 rounded font-mono text-[9px] font-bold bg-indigo-50 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800/40">${(t.sector || 'ALT').replace(/_/g, ' ')}</span>
        </td>
        <td class="py-2 px-1.5 whitespace-nowrap">
          <span class="px-2 py-0.5 rounded font-semibold text-[10px] border ${typeColor}">${t.direction}</span>
        </td>
        <td class="py-2 px-1.5 font-mono text-slate-700 dark:text-slate-300 whitespace-nowrap">
          <div>$${t.entry_price} ➔ $${t.exit_price}</div>
          <span class="inline-block px-1.5 py-0.2 rounded text-[9px] font-sans font-bold bg-purple-50 dark:bg-purple-950/50 text-purple-600 dark:text-purple-300 border border-purple-200 dark:border-purple-800/40">
            ${tf} TF
          </span>
        </td>
        <td class="py-2 px-1.5 font-mono text-slate-500 whitespace-nowrap">${t.bars_held || 1}b</td>
        <td class="py-2 px-1.5 whitespace-nowrap">
          <span class="px-2 py-0.5 rounded text-[10px] font-bold border ${badgeBg}">${t.outcome.replace(/_/g, ' ')}</span>
        </td>
        <td class="py-2 px-2 text-right font-mono ${rColor} whitespace-nowrap">
          <div>${pnlUsdStr}</div>
          <div class="text-[10px] opacity-80">(${t.net_r > 0 ? '+' : ''}${t.net_r} R)</div>
        </td>
        <td class="py-2 px-2.5 text-right text-[10px] text-slate-400 font-mono whitespace-nowrap">${t.exit_time_str || ''}</td>
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
let collapsedJournalCards = new Set();
let isAllJournalCollapsed = false;

function renderBotJournal(trades) {
  const feed = document.getElementById('bot-journal-feed');
  const countBadge = document.getElementById('bot-journal-count');
  const paginationBar = document.getElementById('bot-journal-pagination');
  const pageIndicator = document.getElementById('journal-page-indicator');
  const prevBtn = document.getElementById('btn-journal-prev');
  const nextBtn = document.getElementById('btn-journal-next');
  
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

  feed.innerHTML = pageItems.map(t => {
    const tradeId = t.trade_id || 1;
    const isWin = t.outcome === 'WIN' || t.outcome === 'TRAILING_STOP_WIN' || t.outcome === 'UNLIMITED_RUNNER_WIN';
    const isBE = t.outcome === 'BE_EXIT' || t.outcome === 'BREAKEVEN_DEFENSE';
    const cardBg = isWin ? 'border-emerald-500/20 bg-emerald-50/30 dark:bg-emerald-950/10' : (isBE ? 'border-indigo-500/20 bg-indigo-50/30 dark:bg-indigo-950/10' : 'border-rose-500/20 bg-rose-50/30 dark:bg-rose-950/10');
    const badgeBg = isWin ? 'text-emerald-700 dark:text-emerald-400 bg-emerald-100 dark:bg-emerald-950/60 border-emerald-300 dark:border-emerald-500/30' : (isBE ? 'text-indigo-700 dark:text-indigo-400 bg-indigo-100 dark:bg-indigo-950/60 border-indigo-300 dark:border-indigo-500/30' : 'text-rose-700 dark:text-rose-400 bg-rose-100 dark:bg-rose-950/60 border-rose-300 dark:border-rose-500/30');
    const rColor = t.net_r > 0 ? 'text-emerald-600 dark:text-emerald-400 font-bold' : (t.net_r === 0 ? 'text-indigo-600 dark:text-indigo-400 font-bold' : 'text-rose-600 dark:text-rose-400 font-bold');
    const pnlUsd = t.pnl_usd !== undefined ? t.pnl_usd : round(t.net_r * 1.0, 2);
    const pnlUsdStr = `${pnlUsd >= 0 ? '+' : ''}$${pnlUsd.toFixed(2)}`;

    const ctx = t.pre_trade_context || {
      reason: isWin ? 'Clean squeeze momentum expansion with volume confirmation' : 'Squeeze breakout attempt into key level',
      rvol: 2.1,
      rsi: isWin ? 64.5 : 48.2,
      volatility_atr: 0.05,
      regime: isWin ? 'Bullish Trend & Volatility Expansion' : 'Range Resistance / Pullback'
    };

    let diag = t.diagnostic || {};
    if (!diag.catalyst_type) {
      if (t.outcome === 'WIN') {
        diag = {
          catalyst_type: "Impulsive Momentum Expansion",
          summary: `Rapid target hit in ${t.bars_held || 1} bars. Strong order flow propelled price directly to target without significant drawdown.`,
          key_factors: ["High institutional velocity", "Low adverse excursion (MAE)", "Clean technical extension"]
        };
      } else if (t.outcome === 'TRAILING_STOP_WIN') {
        diag = {
          catalyst_type: "ATR Trailing Stop Protected Profit",
          summary: `Dynamic trailing stop locked in +${t.net_r}R profit as momentum cooled off after favorable extension.`,
          key_factors: ["Dynamic stop protection prevented giving back gains", "Secured runner profit"]
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

    const isCollapsed = collapsedJournalCards.has(tradeId);

    return `
      <div class="border ${cardBg} rounded-xl p-4 text-xs transition-all shadow-sm">
        <!-- Interactive Collapsible Header -->
        <div class="journal-card-header flex items-center justify-between gap-2 cursor-pointer select-none ${isCollapsed ? '' : 'mb-2.5 pb-2 border-b border-slate-200/60 dark:border-gray-800'}" data-trade-id="${tradeId}">
          <div class="flex items-center gap-2 flex-wrap">
            <span class="px-2 py-0.5 rounded bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 font-mono text-[10px] font-bold border border-indigo-200 dark:border-indigo-800/40">#${tradeId}</span>
            <span class="font-bold text-slate-900 dark:text-white text-sm">${t.symbol}</span>
            <span class="px-2 py-0.5 rounded text-[10px] font-semibold border ${badgeBg}">${t.direction}</span>
            <span class="text-slate-400 text-[10px] hidden sm:inline">${t.exit_time_str || ''} (${t.bars_held || 1}b)</span>
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
            <button class="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1 transition-transform duration-200" style="transform: ${isCollapsed ? 'rotate(-90deg)' : 'rotate(0deg)'}">
              <i class="fa-solid fa-chevron-down text-[11px]"></i>
            </button>
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
      if (collapsedJournalCards.has(tid)) {
        collapsedJournalCards.delete(tid);
      } else {
        collapsedJournalCards.add(tid);
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
  const rrEl = document.getElementById('param-target-rr');
  const rvolEl = document.getElementById('param-rvol');
  const slEl = document.getElementById('param-atr-sl');
  const tpEl = document.getElementById('param-atr-tp');
  
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

  if (!optimizations || optimizations.length === 0) {
    container.innerHTML = `
      <div class="text-center py-6 text-slate-400 dark:text-gray-500">
        <i class="fa-solid fa-microchip text-xl mb-1.5 block text-slate-300 dark:text-gray-600"></i>
        The AI evaluates trade cycles and refines parameters every 5 closed trades.
      </div>
    `;
    if (paginationBar) paginationBar.classList.add('hidden');
    return;
  }

  cachedEvoOptimizations = optimizations.slice().reverse();
  const totalItems = cachedEvoOptimizations.length;
  const totalPages = Math.max(1, Math.ceil(totalItems / EVO_PER_PAGE));
  if (currentEvoPage > totalPages) currentEvoPage = totalPages;
  if (currentEvoPage < 1) currentEvoPage = 1;

  const startIndex = (currentEvoPage - 1) * EVO_PER_PAGE;
  const pageItems = cachedEvoOptimizations.slice(startIndex, startIndex + EVO_PER_PAGE);

  container.innerHTML = pageItems.map(opt => {
    const s = opt.summary;
    const isObj = typeof s === 'object' && s !== null;
    return `
      <div class="p-3 rounded-lg border border-slate-200 dark:border-gray-800 bg-slate-50 dark:bg-[#1e293b]/40 shadow-xs">
        <div class="flex items-center justify-between text-[11px] mb-1.5">
          <span class="font-semibold text-slate-800 dark:text-slate-200 flex items-center gap-1.5">
            <i class="fa-solid fa-dna text-purple-500"></i> Multi-Timeframe Optimization Cycle
          </span>
          <span class="text-slate-400 text-[10px]">${opt.timestamp}</span>
        </div>
        ${isObj ? `
          <div class="space-y-1 text-[10px] text-slate-600 dark:text-gray-300 font-mono">
            <div class="flex justify-between"><span>Optimized Timeframe:</span> <b class="text-indigo-600 dark:text-indigo-400">${opt.best_timeframe || s.timeframe || '15m'}</b></div>
            <div class="flex justify-between"><span>Historical Simulation Sample:</span> <b>${s.tested_trades} historical setups</b></div>
            <div class="flex justify-between"><span>Stress-Test Win Rate:</span> <b class="text-emerald-600 dark:text-emerald-400">${s.win_rate_pct}% (Simulated)</b></div>
            <div class="flex justify-between"><span>Net Expectancy:</span> <b class="text-purple-600 dark:text-purple-400">+${s.expectancy_r} R / trade</b></div>
            <div class="flex justify-between"><span>Target RR:</span> <b class="text-emerald-600 dark:text-emerald-400">1:${s.params ? s.params.target_rr : 2.0} RR</b></div>
          </div>
          <p class="text-[9px] text-slate-400 dark:text-gray-500 mt-1.5 italic">*Tested across 200+ historical Binance candles to validate formula before live deployment.*</p>
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


