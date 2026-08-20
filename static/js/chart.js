// Chart Manager using TradingView Lightweight Charts
let mainChart = null;
let momChart = null;

let candleSeries = null;
let ema200Series = null;
let ema50Series = null;
let bbUpperSeries = null;
let bbLowerSeries = null;
let kcUpperSeries = null;
let kcLowerSeries = null;
let momHistogramSeries = null;

// Track active price lines to remove on reload
let activePriceLines = [];

function getChartTheme() {
  const isDark = document.documentElement.classList.contains('dark');
  return {
    layout: {
      background: { color: isDark ? '#111827' : '#ffffff' },
      textColor: isDark ? '#94a3b8' : '#475569',
      fontSize: 11,
      fontFamily: 'Inter, sans-serif'
    },
    grid: {
      vertLines: { color: isDark ? 'rgba(30, 41, 59, 0.5)' : '#f1f5f9' },
      horzLines: { color: isDark ? 'rgba(30, 41, 59, 0.5)' : '#f1f5f9' }
    },
    crosshair: {
      mode: 1, // CrosshairMode.Normal
    },
    timeScale: {
      borderColor: isDark ? '#1e293b' : '#e2e8f0',
      timeVisible: true,
      secondsVisible: false,
    },
    rightPriceScale: {
      borderColor: isDark ? '#1e293b' : '#e2e8f0',
      scaleMargins: {
        top: 0.1,
        bottom: 0.15,
      }
    }
  };
}

function updateChartTheme() {
  if (!mainChart || !momChart) return;
  const theme = getChartTheme();
  mainChart.applyOptions(theme);
  momChart.applyOptions({
    ...theme,
    timeScale: {
      ...theme.timeScale,
      visible: false,
    }
  });
}

function initCharts() {
  const mainContainer = document.getElementById('chart-main');
  const momContainer = document.getElementById('chart-momentum');
  
  if (!mainContainer || !momContainer) return;
  
  // Clear any existing contents
  mainContainer.innerHTML = '';
  momContainer.innerHTML = '';

  const chartTheme = getChartTheme();

  // 1. Create Main Candlestick Chart
  mainChart = LightweightCharts.createChart(mainContainer, {
    ...chartTheme,
    height: 360,
    width: mainContainer.clientWidth,
  });

  // Candlestick series
  candleSeries = mainChart.addCandlestickSeries({
    upColor: '#10b981',
    downColor: '#ef4444',
    borderUpColor: '#10b981',
    borderDownColor: '#ef4444',
    wickUpColor: '#10b981',
    wickDownColor: '#ef4444',
  });

  // Overlay Lines
  ema200Series = mainChart.addLineSeries({
    color: '#f59e0b', // Amber
    lineWidth: 2,
    title: 'EMA 200',
    crosshairMarkerVisible: false,
  });

  ema50Series = mainChart.addLineSeries({
    color: '#3b82f6', // Blue
    lineWidth: 1.5,
    title: 'EMA 50',
    crosshairMarkerVisible: false,
  });

  bbUpperSeries = mainChart.addLineSeries({
    color: '#ec4899', // Pink
    lineWidth: 1,
    lineStyle: 2, // Dashed
    crosshairMarkerVisible: false,
  });

  bbLowerSeries = mainChart.addLineSeries({
    color: '#ec4899',
    lineWidth: 1,
    lineStyle: 2,
    crosshairMarkerVisible: false,
  });

  kcUpperSeries = mainChart.addLineSeries({
    color: '#06b6d4', // Cyan
    lineWidth: 1,
    crosshairMarkerVisible: false,
  });

  kcLowerSeries = mainChart.addLineSeries({
    color: '#06b6d4',
    lineWidth: 1,
    crosshairMarkerVisible: false,
  });

  // 2. Create Squeeze Momentum Sub-Chart
  momChart = LightweightCharts.createChart(momContainer, {
    ...chartTheme,
    height: 100,
    width: momContainer.clientWidth,
    timeScale: {
      ...chartTheme.timeScale,
      visible: false, // Time axis on top chart
    }
  });

  momHistogramSeries = momChart.addHistogramSeries({
    color: '#10b981',
    priceFormat: {
      type: 'volume',
    },
    priceScaleId: '',
  });

  // Sync timescales
  mainChart.timeScale().subscribeVisibleLogicalRangeChange(range => {
    if (range && momChart) {
      momChart.timeScale().setVisibleLogicalRange(range);
    }
  });

  momChart.timeScale().subscribeVisibleLogicalRangeChange(range => {
    if (range && mainChart) {
      mainChart.timeScale().setVisibleLogicalRange(range);
    }
  });

  // Responsive resize
  window.addEventListener('resize', () => {
    if (mainChart && mainContainer) {
      mainChart.applyOptions({ width: mainContainer.clientWidth });
    }
    if (momChart && momContainer) {
      momChart.applyOptions({ width: momContainer.clientWidth });
    }
  });
}

function updateChartData(data) {
  if (!mainChart || !candleSeries) {
    initCharts();
  }

  // 1. Set Candle and indicator series
  candleSeries.setData(data.candles);
  if (data.ema200 && data.ema200.length) ema200Series.setData(data.ema200);
  if (data.ema50 && data.ema50.length) ema50Series.setData(data.ema50);
  if (data.bb_upper && data.bb_upper.length) bbUpperSeries.setData(data.bb_upper);
  if (data.bb_lower && data.bb_lower.length) bbLowerSeries.setData(data.bb_lower);
  if (data.kc_upper && data.kc_upper.length) kcUpperSeries.setData(data.kc_upper);
  if (data.kc_lower && data.kc_lower.length) kcLowerSeries.setData(data.kc_lower);
  if (data.momentum_bars && data.momentum_bars.length) momHistogramSeries.setData(data.momentum_bars);

  // 2. Clear old price lines
  activePriceLines.forEach(line => {
    try { candleSeries.removePriceLine(line); } catch (e) {}
  });
  activePriceLines = [];

  // 3. Draw Dynamic Entry, Stop Loss, and TP1-TP4 Price Lines
  const rr = data.current_metrics.rr_levels;
  if (rr) {
    const slLine = candleSeries.createPriceLine({
      price: rr.stop_loss,
      color: '#f43f5e', // Rose
      lineWidth: 2,
      lineStyle: 1, // Dotted
      axisLabelVisible: true,
      title: 'SL (-1.5 ATR)',
    });
    activePriceLines.push(slLine);

    const entryLine = candleSeries.createPriceLine({
      price: rr.entry,
      color: '#3b82f6', // Blue
      lineWidth: 1.5,
      lineStyle: 0, // Solid
      axisLabelVisible: true,
      title: 'Entry',
    });
    activePriceLines.push(entryLine);

    const tp1Line = candleSeries.createPriceLine({
      price: rr.tp1_1rr,
      color: '#10b981', // Emerald
      lineWidth: 1.5,
      lineStyle: 2, // Dashed
      axisLabelVisible: true,
      title: 'TP1 (1:1)',
    });
    activePriceLines.push(tp1Line);

    const tp2Line = candleSeries.createPriceLine({
      price: rr.tp2_2rr,
      color: '#34d399',
      lineWidth: 2,
      lineStyle: 2,
      axisLabelVisible: true,
      title: 'TP2 (1:2)',
    });
    activePriceLines.push(tp2Line);

    const tp3Line = candleSeries.createPriceLine({
      price: rr.tp3_3rr,
      color: '#6ee7b7',
      lineWidth: 1.5,
      lineStyle: 2,
      axisLabelVisible: true,
      title: 'TP3 (1:3)',
    });
    activePriceLines.push(tp3Line);

    const tp4Line = candleSeries.createPriceLine({
      price: rr.tp4_4rr,
      color: '#c084fc', // Purple
      lineWidth: 2,
      lineStyle: 2,
      axisLabelVisible: true,
      title: 'TP4 (1:4)',
    });
    activePriceLines.push(tp4Line);
  }

  mainChart.timeScale().fitContent();
}
