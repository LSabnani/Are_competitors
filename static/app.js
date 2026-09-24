document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('compare-form');
  const companyAInput = document.getElementById('company-a');
  const companyBInput = document.getElementById('company-b');
  const submitBtn = document.getElementById('submit-btn');
  const btnSpinner = document.getElementById('btn-spinner');
  const resetBtn = document.getElementById('reset-btn');
  const chipBtns = document.querySelectorAll('.chip-btn');
  const resultsSection = document.getElementById('results-section');
  const comparisonGrid = document.getElementById('comparison-grid');
  const compareAnotherBtn = document.getElementById('compare-another-btn');
  const historyList = document.getElementById('history-list');
  const emptyHistory = document.getElementById('empty-history');
  const historyCount = document.getElementById('history-count');

  let sessionHistory = [];

  // Handle Preset Pair Chips
  chipBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      companyAInput.value = btn.getAttribute('data-a');
      companyBInput.value = btn.getAttribute('data-b');
      form.dispatchEvent(new Event('submit'));
    });
  });

  // Handle Reset Button
  resetBtn.addEventListener('click', () => {
    companyAInput.value = '';
    companyBInput.value = '';
    resultsSection.hidden = true;
    companyAInput.focus();
  });

  // Handle "Compare Another Pair" Re-prompt Button
  compareAnotherBtn.addEventListener('click', async () => {
    companyAInput.value = '';
    companyBInput.value = '';
    resultsSection.hidden = true;
    window.scrollTo({ top: 0, behavior: 'smooth' });
    companyAInput.focus();
    
    // Clear old information from cache as per spec
    try {
      await fetch('/api/v1/clear_cache', { method: 'POST' });
    } catch (e) {
      console.log('Cache cleared');
    }
  });


  // Handle Form Submit
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const compA = companyAInput.value.trim();
    const compB = companyBInput.value.trim();
    const tickA = document.getElementById('ticker-a') ? document.getElementById('ticker-a').value.trim() : '';
    const tickB = document.getElementById('ticker-b') ? document.getElementById('ticker-b').value.trim() : '';

    if (!compA || !compB) return;

    // Loading UI state
    submitBtn.disabled = true;
    btnSpinner.hidden = false;

    try {
      const response = await fetch('/api/v1/compare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ companyA: compA, companyB: compB, tickerA: tickA, tickerB: tickB })
      });

      const resData = await response.json();

      if (response.ok && resData.data) {
        renderComparisonCards(resData.data.companyA, resData.data.companyB, resData.marketAnalysis);
        addToHistory(compA, compB, resData);
      } else {
        alert(resData.message || 'An error occurred while fetching company data.');
      }

    } catch (err) {
      console.error(err);
      alert('Network error. Unable to reach backend service.');
    } finally {
      submitBtn.disabled = false;
      btnSpinner.hidden = true;
    }
  });

  // Render Side-by-Side Comparison Cards with Slide 3 Market Size & Market Share Page
  function renderComparisonCards(itemA, itemB, marketAnalysis) {
    let marketBannerHTML = '';
    if (marketAnalysis) {
      marketBannerHTML = `
        <div class="market-segment-card card-panel">
          <div class="market-segment-header">
            <div class="segment-title-wrapper">
              <span class="segment-badge">${escapeHTML(marketAnalysis.overlapType)}</span>
              <span class="leader-badge">Leader: ${escapeHTML(marketAnalysis.marketLeader)}</span>
            </div>
            <h4>Slide 3 — Market Size & Share: <span>${escapeHTML(marketAnalysis.commonSegment)}</span></h4>
          </div>

          <div class="market-size-grid">
            <div class="market-stat">
              <span class="stat-label">Segment Market Size (TAM)</span>
              <span class="stat-value highlight">${escapeHTML(marketAnalysis.segmentMarketSize)}</span>
            </div>
            <div class="market-stat">
              <span class="stat-label">${escapeHTML(itemA.officialName || itemA.inputName)} Share</span>
              <span class="stat-value comp-a-color">${escapeHTML(marketAnalysis.shareA)}</span>
            </div>
            <div class="market-stat">
              <span class="stat-label">${escapeHTML(itemB.officialName || itemB.inputName)} Share</span>
              <span class="stat-value comp-b-color">${escapeHTML(marketAnalysis.shareB)}</span>
            </div>
            <div class="market-stat">
              <span class="stat-label">Remaining Industry Share</span>
              <span class="stat-value muted">${escapeHTML(marketAnalysis.remainingShare)}</span>
            </div>
          </div>

          <!-- Market Share Visual Meter -->
          <div class="share-meter-container">
            <div class="share-meter-label">Market Share Breakdown</div>
            <div class="share-meter-bar">
              <div class="share-segment bar-comp-a" style="width: ${marketAnalysis.rawShareA}%;" title="${escapeHTML(itemA.officialName)}: ${marketAnalysis.shareA}"></div>
              <div class="share-segment bar-comp-b" style="width: ${marketAnalysis.rawShareB}%;" title="${escapeHTML(itemB.officialName)}: ${marketAnalysis.shareB}"></div>
              <div class="share-segment bar-other" style="width: ${marketAnalysis.rawRemaining}%;" title="Other Industry Players: ${marketAnalysis.remainingShare}"></div>
            </div>
            <div class="share-meter-legend">
              <span class="legend-item"><span class="dot comp-a"></span> ${escapeHTML(itemA.officialName || itemA.inputName)} (${marketAnalysis.shareA})</span>
              <span class="legend-item"><span class="dot comp-b"></span> ${escapeHTML(itemB.officialName || itemB.inputName)} (${marketAnalysis.shareB})</span>
              <span class="legend-item"><span class="dot other"></span> Other Players (${marketAnalysis.remainingShare})</span>
            </div>
          </div>
        </div>
      `;
    }


    comparisonGrid.innerHTML = `
      ${marketBannerHTML}
      <div class="cards-wrapper-grid">
        ${createCardHTML(itemA, 'Company A')}
        ${createCardHTML(itemB, 'Company B')}
      </div>
    `;
    resultsSection.hidden = false;
    resultsSection.scrollIntoView({ behavior: 'smooth' });
  }


  function createCardHTML(item, label) {
    if (!item.isPublic) {
      return `
        <div class="comp-card">
          <div class="comp-card-header">
            <div class="comp-card-title">
              <h4>${escapeHTML(item.inputName)}</h4>
            </div>
            <span class="status-badge status-unlisted">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="8" x2="12" y2="12"></line>
                <line x1="12" y1="16" x2="12.01" y2="16"></line>
              </svg>
              Not Public / Unlisted
            </span>
          </div>
          <div class="summary-box">
            <p>${escapeHTML(item.message || 'Company may not be public or listed on major stock exchanges.')}</p>
          </div>
        </div>
      `;
    }

    return `
      <div class="comp-card">
        <div class="comp-card-header">
          <div class="comp-card-title">
            <h4>${escapeHTML(item.officialName || item.inputName)}</h4>
            <span class="ticker-badge">${escapeHTML(item.ticker)}</span>
          </div>
          <span class="status-badge status-public">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
              <polyline points="22 4 12 14.01 9 11.01"></polyline>
            </svg>
            Publicly Traded (${item.ticker})
          </span>
        </div>

        <a href="${escapeHTML(item.sourceUrl)}" target="_blank" rel="noopener" class="source-link">
          View on Barchart.com
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
            <polyline points="15 3 21 3 21 9"></polyline>
            <line x1="10" y1="14" x2="21" y2="3"></line>
          </svg>
        </a>

        <div class="summary-slide slide-1">
          <h5>Slide 1 — Business Summary (4 Bullet Points)</h5>
          <ul class="slide-bullets">
            ${(item.bullets || []).map(b => `<li>${formatMarkdownBold(escapeHTML(b))}</li>`).join('')}
          </ul>
        </div>

        ${item.financials ? `
        <div class="financials-slide slide-2">
          <h5>Slide 2 — Income Statement & Balance Sheet</h5>
          <div class="financial-tables-grid">
            <div class="fin-table-block">
              <h6>Income Statement</h6>
              <table class="fin-table">
                <tr><td>Revenue (TTM):</td><td><strong>${escapeHTML(item.financials.incomeStatement.totalRevenue)}</strong></td></tr>
                <tr><td>Gross Profit:</td><td><strong>${escapeHTML(item.financials.incomeStatement.grossProfit)}</strong></td></tr>
                <tr><td>Operating Margin:</td><td><strong>${escapeHTML(item.financials.incomeStatement.operatingIncome)}</strong></td></tr>
                <tr><td>Net Income:</td><td><strong>${escapeHTML(item.financials.incomeStatement.netIncome)}</strong></td></tr>
                <tr><td>Trailing EPS:</td><td><strong>${escapeHTML(item.financials.incomeStatement.trailingEps)}</strong></td></tr>
              </table>
            </div>

            <div class="fin-table-block">
              <h6>Balance Sheet</h6>
              <table class="fin-table">
                <tr><td>Total Cash:</td><td><strong>${escapeHTML(item.financials.balanceSheet.totalCash)}</strong></td></tr>
                <tr><td>Total Debt:</td><td><strong>${escapeHTML(item.financials.balanceSheet.totalDebt)}</strong></td></tr>
                <tr><td>Book Value:</td><td><strong>${escapeHTML(item.financials.balanceSheet.bookValue)}</strong></td></tr>
              </table>
            </div>
          </div>
        </div>
        ` : ''}

        <div class="summary-box">
          <h5>Barchart Full Profile Overview</h5>
          <p>${escapeHTML(item.summary)}</p>
        </div>
      </div>
    `;
  }


  function formatMarkdownBold(str) {
    return str.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  }


  // Session History Logging
  function addToHistory(compA, compB, fullData) {
    const entry = {
      pair: `${compA} vs ${compB}`,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      data: fullData
    };

    sessionHistory.unshift(entry);
    updateHistoryUI();
  }

  function updateHistoryUI() {
    historyCount.textContent = `${sessionHistory.length} item${sessionHistory.length === 1 ? '' : 's'}`;
    if (sessionHistory.length === 0) {
      emptyHistory.hidden = false;
      historyList.innerHTML = '';
      return;
    }

    emptyHistory.hidden = true;
    historyList.innerHTML = sessionHistory.map((item, idx) => `
      <li class="history-item" data-index="${idx}">
        <span class="history-pair">${escapeHTML(item.pair)}</span>
        <span class="history-time">${item.time}</span>
      </li>
    `).join('');

    // Re-click history item to reload comparison
    document.querySelectorAll('.history-item').forEach(el => {
      el.addEventListener('click', () => {
        const idx = el.getAttribute('data-index');
        const item = sessionHistory[idx];
        if (item && item.data && item.data.data) {
          renderComparisonCards(item.data.data.companyA, item.data.data.companyB);
        }
      });
    });
  }

  function escapeHTML(str) {
    if (!str) return '';
    return str.replace(/[&<>'"]/g, 
      tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
    );
  }
});
