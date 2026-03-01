import json
import numpy as np
import yfinance as yf
from scipy.optimize import minimize

def get_all_params():
    profiles = ["aggressive", "balanced", "conservative"]
    result = []
    for profile in profiles:
        with open(f"risk_profiles/{profile}.json", "r") as f:
            data = json.load(f)
        means = [v["mean"] for v in data.values()]
        mins = [v["min"] for v in data.values()]
        maxs = [v["max"] for v in data.values()]
        weights = [v["weight"] for v in data.values()]
        result.append((means, mins, maxs, weights))
    return result

def get_all_metrics(stock_name: str) -> tuple:
    stock = yf.Ticker(stock_name)
    info = stock.info
    fast_info = stock.fast_info
    cashflow = stock.cashflow
    financials = stock.financials
    balance_sheet = stock.balance_sheet

    sector = info["sector"]
    price = fast_info['last_price']
    roe = info["returnOnEquity"]
    de_ratio = info["debtToEquity"]
    current_ratio = info["currentRatio"]
    pe_ratio = info["trailingPE"]
    ev_ebitda = info["enterpriseToEbitda"]

    revenue_series = financials.loc["Total Revenue"].sort_index(ascending=True)
    if len(revenue_series) >= 4:
        start_revenue = revenue_series.iloc[-4]
        end_revenue = revenue_series.iloc[-1]
        cagr_3yr = (end_revenue / start_revenue) ** (1/3) - 1
    else:
        cagr_3yr = 0

    eps_growth = info["earningsGrowth"]
    fcf_series = cashflow.loc["Free Cash Flow"].sort_index(ascending=True)
    if len(fcf_series) >= 2:
        fcf_start = fcf_series.iloc[-2]
        fcf_end = fcf_series.iloc[-1]
        fcf_growth = (fcf_end - fcf_start) / fcf_start * 100
    else:
        fcf_growth = 0

    data = stock.history(period="6mo", interval="1d")["Close"].diff()
    gain = data.clip(lower=0)
    loss = -data.clip(upper=0)
    window = 14
    avg_gain = gain.rolling(window=window, min_periods=window).mean()
    avg_loss = loss.rolling(window=window, min_periods=window).mean()
    rs = avg_gain / avg_loss
    rsi_series = 100 - (100 / (1 + rs))
    rsi = rsi_series.iloc[-1]
    beta = info["beta"]
    price_vs_200dma = info["twoHundredDayAverageChangePercent"]

    total_assets = balance_sheet.loc['Total Assets'].iloc[0]
    working_capital = balance_sheet.loc['Working Capital'].iloc[0]
    retained_earnings = balance_sheet.loc['Retained Earnings'].iloc[0]
    ebit = financials.loc['EBIT'].iloc[0]
    total_liabilities = balance_sheet.loc['Total Liabilities Net Minority Interest'].iloc[0]
    market_cap = info['marketCap']
    revenue = financials.loc['Total Revenue'].iloc[0]
    A = working_capital / total_assets
    B = retained_earnings / total_assets
    C = ebit / total_assets
    D = market_cap / total_liabilities
    E = revenue / total_assets
    altman_z_score = 1.2*A + 1.4*B + 3.3*C + 0.6*D + 1.0*E

    return sector, price, (
        roe, de_ratio, current_ratio, pe_ratio, ev_ebitda, cagr_3yr,
        eps_growth, fcf_growth, rsi, beta, price_vs_200dma, altman_z_score
    )

def get_normalized_value(value, mean: float, minimum, maximum, range=6) -> float:
    std_dev = (maximum - minimum) / range
    coefficient = 1 / (std_dev * np.sqrt((2 * np.pi)))
    exponent = np.exp((-0.5 * ((value - mean) / std_dev) ** 2))
    return coefficient * exponent

def get_asset_score(metric_weights, metric_scores):
    asset_score = 0
    for metric_weight, metric_score in zip(metric_weights, metric_scores):
        asset_score += metric_weight * metric_score
    return asset_score

def get_category_score(category_deposition, asset_depositions, asset_scores):
    asset_weights = [asset_deposition / category_deposition for asset_deposition in asset_depositions]
    category_score = diversification_penalty = 0
    for asset_weight, asset_score in zip(asset_weights, asset_scores):
        category_score += asset_weight * asset_score
        diversification_penalty += asset_weight ** 2
    category_score *= (1 - diversification_penalty) * (1000 / 998)
    return category_score

def get_portfolio_score(portfolio_deposition, category_depositions, category_scores):
    category_weights = [category_deposition / portfolio_deposition for category_deposition in category_depositions]
    portfolio_score = diversification_penalty = 0
    for category_weight, category_score in zip(category_weights, category_scores):
        portfolio_score += category_weight * category_score
        diversification_penalty += category_weight ** 2
    portfolio_score *= (1 - diversification_penalty) / 0.998
    return portfolio_score

def get_all_assets(risk_profile):
    stocks = [
        "TCS.NS", "RELIANCE.NS", "BHARTIARTL.NS", "LT.NS", "ITC.NS", "MARUTI.NS", "HCLTECH.NS",
        "SUNPHARMA.NS", "ONGC.NS", "VEDL.NS", "ADANIPORTS.NS", "HAL.NS", "NESTLEIND.NS", "JSL.NS",
        "ASHOKLEY.NS", "DLF.NS", "PIDILITIND.NS", "NATIONALUM.NS", "NMDC.NS", "NTPC.NS", "HEROMOTOCO.NS"
    ]
    aggressive_data, balanced_data, conservative_data = get_all_params()
    risk_profiles = {
        "aggressive": aggressive_data,
        "balanced": balanced_data,
        "conservative": conservative_data
    }
    means, mins, maxs, weights = risk_profiles[risk_profile]
    stocks_scores = {}
    for stock in stocks:
        sector, _, metrics = get_all_metrics(stock)
        scores = [get_normalized_value(m, mean, _min, _max) for m, mean, _min, _max
                    in zip(metrics, means, mins, maxs)]
        stocks_scores[stock] = {"score": get_asset_score(weights, scores), "sector": sector}
    return stocks_scores

def get_optimized_weights(scores, sectors):
    scores = np.array(scores, dtype=float)
    n = len(scores)
    unique_sectors = sorted(list(set(sectors)))
    sector_indices = [np.where(np.array(sectors) == s)[0] for s in unique_sectors]

    def softmax(z):
        ex = np.exp(z - np.max(z))
        return ex / np.sum(ex)

    def objective(z):
        weights = softmax(z)
        sector_scores_val = []
        sector_weights_val = []
        for indices in sector_indices:
            w_sub = weights[indices]
            s_sub = scores[indices]
            w_total = np.sum(w_sub)
            if w_total < 1e-6:
                sec_score = 0.0
            else:
                w_norm = w_sub / w_total
                raw = np.dot(w_norm, s_sub)
                div = np.dot(w_norm, w_norm)
                sec_score = raw * (1 - div) * (1000.0 / 998.0)
            sector_scores_val.append(sec_score)
            sector_weights_val.append(w_total)
        sector_scores_val = np.array(sector_scores_val)
        sector_weights_val = np.array(sector_weights_val)
        port_raw = np.dot(sector_weights_val, sector_scores_val)
        port_div = np.dot(sector_weights_val, sector_weights_val)
        final_score = port_raw * (1 - port_div) / 0.998
        return -final_score

    res = minimize(objective, np.zeros(n), method='L-BFGS-B')
    weights = softmax(res.x)
    FIS = -objective(res.x)
    return FIS, weights

def get_quantity(stock_name, amount):
    stock = yf.Ticker(stock_name)
    price = stock.fast_info['last_price']
    return price, int(amount / price)
