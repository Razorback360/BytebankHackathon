import os
import pandas as pd
import requests
import numpy as np
import scipy.optimize as sco
import os
from dotenv import load_dotenv
from decimal import Decimal
from pydantic import BaseModel
from enum import StrEnum
import yfinance as yf

load_dotenv(override=True)

class OptimizerResult(BaseModel):
    weights: dict[str,float]
    sharpe_ratio: float
    budget_allocation: dict[str, float]
    target_return: float
    volatility: float

class StockMarket(StrEnum):
    US = "US"
    SA = "SR"

class PortfolioOptimizer:


    def __init__(self, tickers: list[str], stock_market: StockMarket) -> None:
        self.tickers = tickers
        self.stock_market = stock_market
        self.dates = None
        tickers_df = self.__extract_data()
        self.normalized_df = self.__normalize_data(tickers_df)
        self.mean_returns = np.array([self.normalized_df.mean()[ticker] for ticker in self.tickers])
        self.cov = np.array(self.normalized_df.cov())
        self.n = len(self.tickers)

    
    def __extract_data(self) -> pd.DataFrame:
        """
        Fetches historical data using yfinance.
        - market: StockMarket Enum (US or SA).
        """
        # 1. Adjust tickers based on the selected market
        formatted_tickers = []
        for ticker in self.tickers:
            if self.stock_market == StockMarket.SA:
                # Append suffix for Saudi market (e.g., 1120 -> 1120.SR)
                formatted_tickers.append(f"{ticker}.{self.stock_market.value}")
            else:
                # Default for US (no suffix needed usually)
                formatted_tickers.append(ticker)

        # 2. Download data in batch (more efficient than looping)
        # using 'auto_adjust=True' gets the Adjusted Close directly as 'Close'
        print(f"Downloading data for: {formatted_tickers}")
        data = yf.download(formatted_tickers, period="1y", auto_adjust=True, progress=False)

        if len(self.tickers) == 1:

            prices_df = pd.DataFrame(data['Close'])
            prices_df.columns = self.tickers
        else:
            prices_df = data['Close']
            
            if self.stock_market == StockMarket.SA:
                prices_df.columns = [col.replace(f".{self.stock_market.value}", "") for col in prices_df.columns]

        # Ensure no missing data (forward fill then drop remaining)
        return prices_df.ffill().dropna()

    def __normalize_data(self, tickers_df: pd.DataFrame) -> pd.DataFrame:
        return tickers_df.pct_change().dropna()
    
    def _minimize_risks(self, daily_reward, budget: Decimal, allow_short=False):
        """
        Minimize portfolio variance subject to:
        - Expected return = daily_reward
        - Sum of weights = 1
        - Optional: No short selling (w >= 0)
        """
        budget = float(budget)
        def objective(w):
            return w @ self.cov @ w
        
        # Constraints
        constraints = [
            {'type': 'eq', 'fun': lambda w: self.mean_returns @ w - daily_reward},  # Target return
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}  # Fully invested
        ]
        
        # Bounds
        if allow_short:
            bounds = [(None, None)] * self.n
        else:
            bounds = [(0, None)] * self.n  # No short selling
        
        # Initial guess: equal weights
        w0 = np.ones(self.n) / self.n
        
        # Optimize
        result = sco.minimize(objective, w0, method='SLSQP', bounds=bounds, constraints=constraints)
        
        if not result.success:
            print(f"Warning: Optimization did not converge. Message: {result.message}")
        
        w = result.x
        
        # Build results
        results = {self.tickers[i]: float(w[i]) * budget for i in range(self.n)}
        results['daily_variance'] = float(w @ self.cov @ w)
        results['daily_return'] = float(self.mean_returns @ w * budget)
        results['daily_std'] = float(np.sqrt(w @ self.cov @ w) * budget)
        results['optimization_success'] = result.success
        
        return results
    

    
    def efficient_frontier(self, budget: Decimal, n_points=50, allow_short=False):
        """
        Compute the efficient frontier: optimal portfolios for different return levels
        
        Returns: List of dictionaries with portfolio weights and statistics
        """
        min_return = np.min(self.mean_returns)
        max_return = np.max(self.mean_returns)
        budget = float(budget)
        target_returns = np.linspace(min_return, max_return, n_points)
        frontier = []
        
        for target in target_returns:
            try:
                result = self._minimize_risks(target, budget=budget, allow_short=allow_short)
                if result['optimization_success']:
                    frontier.append({
                        'target_return': target,
                        'variance': result['daily_variance'],
                        'std': np.sqrt(result['daily_variance']),
                        'weights': {k: v/budget if budget > 0 else v 
                                   for k, v in result.items() 
                                   if k in self.tickers}
                    })
            except Exception as e:
                print(e)
                continue
        return frontier
    
    def return_highest_sharpe_ratio(self, budget: Decimal, allow_short=False)->OptimizerResult:
        """
        Find the portfolio with the highest Sharpe ratio
        
        Returns: Dictionary with portfolio weights and statistics
        """
        
        ef = self.efficient_frontier(budget=budget, allow_short=allow_short)
        best_portfolio = None
    
        risk_free_rate = 0.03 / 252 # Assuming 3% annual risk-free rate

        max_sharpe_ratio = -np.inf
        portfolio_index = -1

        for i, portfolio in enumerate(ef):
            expected_return = portfolio['target_return']
            std_dev = portfolio['std']
            sharpe_ratio = (expected_return - risk_free_rate) / std_dev
            
            if sharpe_ratio > max_sharpe_ratio:
                max_sharpe_ratio = sharpe_ratio
                portfolio_index = i

        best_portfolio = ef[portfolio_index] if portfolio_index >= 0 else None
        allocation_budget = {k: v * float(budget) for k, v in best_portfolio['weights'].items()} if best_portfolio else None
        return OptimizerResult(
            weights=best_portfolio['weights'] if best_portfolio else {},
            sharpe_ratio=max_sharpe_ratio,
            budget_allocation=allocation_budget if allocation_budget else {},
            target_return=best_portfolio.get("target_return"),
            volatility=best_portfolio.get("daily_variance") * np.sqrt(252)
            
        )
        


if __name__ == '__main__':
    optimizer = PortfolioOptimizer(['GOOGL', 'NVDA', 'AAPL'], StockMarket.US)
    result  = optimizer.return_highest_sharpe_ratio(budget = Decimal('10000'))
    print(result)
