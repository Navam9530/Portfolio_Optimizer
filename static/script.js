function switchTab(tab) {
    // Update buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');

    // Update sections
    document.querySelectorAll('.card').forEach(section => {
        section.classList.remove('active-section');
    });

    if (tab === 'fis') {
        document.getElementById('fis-section').classList.add('active-section');
    } else {
        document.getElementById('optimize-section').classList.add('active-section');
    }
}

function addStockRow() {
    const container = document.getElementById('portfolio-inputs');
    const row = document.createElement('div');
    row.className = 'stock-row';
    row.innerHTML = `
        <input type="text" placeholder="Ticker (e.g. AAPL)" class="stock-ticker" required>
        <input type="number" placeholder="Qty" class="stock-quantity" min="0" step="any" required>
        <button type="button" class="btn-remove" onclick="removeRow(this)">×</button>
    `;
    container.appendChild(row);
    updateRemoveButtons();
}

function removeRow(btn) {
    btn.parentElement.remove();
    updateRemoveButtons();
}

function updateRemoveButtons() {
    const rows = document.querySelectorAll('.stock-row');
    rows.forEach(row => {
        const btn = row.querySelector('.btn-remove');
        if (rows.length > 1) {
            btn.style.visibility = 'visible';
        } else {
            btn.style.visibility = 'hidden';
        }
    });
}

function showLoading(sectionId) {
    document.getElementById(sectionId).classList.add('loading');
}

function hideLoading(sectionId) {
    document.getElementById(sectionId).classList.remove('loading');
}

document.getElementById('fis-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const resultBox = document.getElementById('fis-result');
    resultBox.classList.add('hidden');
    showLoading('fis-section');

    const risk = document.getElementById('fis-risk').value;

    const portfolio = {};
    document.querySelectorAll('.stock-row').forEach(row => {
        const ticker = row.querySelector('.stock-ticker').value.toUpperCase();
        const quantity = parseFloat(row.querySelector('.stock-quantity').value);
        if (ticker && quantity) {
            portfolio[ticker] = quantity;
        }
    });

    try {
        const response = await fetch('/getFIS', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                risk_profile: risk,
                portfolio: portfolio
            })
        });

        const data = await response.json();

        resultBox.innerHTML = `<h3>Result</h3><p>${data}</p>`;
        resultBox.classList.remove('hidden');
    } catch (err) {
        alert('Server Error');
        console.error(err);
    } finally {
        hideLoading('fis-section');
    }
});

document.getElementById('optimize-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const resultBox = document.getElementById('optimize-result');
    resultBox.classList.add('hidden');
    showLoading('optimize-section');

    const risk = document.getElementById('opt-risk').value;
    const budget = document.getElementById('opt-budget').value;

    try {
        const response = await fetch(`/getOptimizedPortfolio?risk_profile=${risk}&budget=${budget}`);
        const data = await response.json();

        let html = `<h3>Optimization Result</h3>`;
        html += `<p class="score">${data.score}</p>`;
        html += `<div class="portfolio-list">`;

        for (const [stock, details] of Object.entries(data.portfolio)) {
            html += `
                <div class="portfolio-item">
                    <div class="info-box name-box">
                        <span class="label">Stock</span>
                        <span class="value">${stock}</span>
                    </div>
                    <div class="info-box qty-box">
                        <span class="label">Quantity</span>
                        <span class="value">${Math.floor(details.quantity)}</span>
                    </div>
                    <div class="info-box price-box">
                        <span class="label">Price</span>
                        <span class="value">₹${details.price.toFixed(2)}</span>
                    </div>
                </div>
            `;
        }
        html += `</div>`;

        resultBox.innerHTML = html;
        resultBox.classList.remove('hidden');
    } catch (err) {
        alert('Server Error');
        console.error(err);
    } finally {
        hideLoading('optimize-section');
    }
});
