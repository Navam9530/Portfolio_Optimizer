from utils import (
    get_all_params, get_all_metrics, get_normalized_value, get_asset_score, get_category_score, get_portfolio_score,
    get_all_assets, get_optimized_weights, get_quantity
)

SECTORS = [
    "Industrials", "Financial Services", "Healthcare", "Technology",
    "Basic Materials", "Energy", "Consumer Cyclical", "Consumer Defensive",
    "Utilities", "Communication Services", "Real Estate"
]

def FIS(risk_profile, portfolio):
    aggressive_data, balanced_data, conservative_data = get_all_params()
    risk_profiles = {
        "aggressive": aggressive_data,
        "balanced": balanced_data,
        "conservative": conservative_data
    }

    # Asset Scores
    sector_scores = {sector: {rp: [] for rp in risk_profiles} for sector in SECTORS}
    sector_depositions = {sector: [] for sector in SECTORS}
    for stock, quantity in portfolio.items():
        sector, price, metrics = get_all_metrics(stock)
        for rp_name, (means, mins, maxs, weights) in risk_profiles.items():
            metric_scores = [get_normalized_value(m, mean, _min, _max) for m, mean, _min, _max
                             in zip(metrics, means, mins, maxs)]
            asset_score = get_asset_score(weights, metric_scores)
            sector_scores[sector][rp_name].append(asset_score)
        sector_depositions[sector].append(quantity * price)

    # Sector Scores
    sector_totals = {sector: sum(sector_depositions[sector]) for sector in SECTORS}
    portfolio_deposition = sum(sector_totals.values())
    risk_profile_sector_scores = {rp: [] for rp in risk_profiles}
    for sector in SECTORS:
        total_dep = sector_totals[sector]
        deposits = sector_depositions[sector]
        for rp_name in risk_profiles:
            scores = sector_scores[sector][rp_name]
            sector_score = get_category_score(total_dep, deposits, scores)
            risk_profile_sector_scores[rp_name].append(sector_score)

    # Portfolio Scores
    portfolio_scores = {
        rp: get_portfolio_score(portfolio_deposition, list(sector_totals.values()), scores)
        for rp, scores in risk_profile_sector_scores.items()
    }

    # Report
    max_FIS_name = max(portfolio_scores, key=portfolio_scores.get)
    if risk_profile != max_FIS_name:
        risk_profile_match = f"You described yourself as {risk_profile} investor, but your portfolio is {max_FIS_name}"
    else:
        risk_profile_match = f"Your portfolio matches with your risk profile: {risk_profile}"
    portfolio_score = portfolio_scores[risk_profile] * 100
    return f"Your FIS is {portfolio_score:.2f}%. {risk_profile_match}"

def optimized_portfolio(risk_profile, budget):
    assets = get_all_assets(risk_profile)
    asset_names = list(assets.keys())
    asset_scores = [v["score"] for v in assets.values()]
    asset_sectors = [v["sector"] for v in assets.values()]
    portfolio_score, weights = get_optimized_weights(asset_scores, asset_sectors)
    amounts = budget * weights
    prices, quantities = zip(*(get_quantity(asset, amount) for asset, amount in zip(asset_names, amounts)))
    optimized_portfolio = {asset_name: {"price": price, "quantity": quantity}
                           for asset_name, price, quantity in zip(asset_names, prices, quantities)}
    return f"Optimized FIS is {float(portfolio_score * 100):.2f}%", optimized_portfolio
