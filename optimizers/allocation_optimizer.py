import os
import pandas as pd
import requests
import numpy as np
import scipy.optimize as sco
import os
from dotenv import load_dotenv
from decimal import Decimal
from pydantic import BaseModel

load_dotenv(override=True)

class OptimizerResult(BaseModel):
    weights: dict[str,float]
    sharpe_ratio: float
    budget_allocation: dict[str, float]

class PortfolioOptimizer:


    def __init__(self, tickers: list[str] ) -> None:
        self.tickers = tickers
        self.dates = None
        tickers_df = self.__extract_data()
        self.normalized_df = self.__normalize_data(tickers_df)
        self.mean_returns = np.array([self.normalized_df.mean()[ticker] for ticker in self.tickers])
        self.cov = np.array(self.normalized_df.cov())
        self.n = len(self.tickers)

    
    def __extract_data(self) -> None:

        final_dates = None
        prices_dict = {}
        for ticker in self.tickers:
            symbol = ticker.upper()
            url = f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&interval=5min&outputsize=compact&apikey={os.environ.get("ALPHA_VANTAGE_API_KEY")}'
            r = requests.get(url)
            data = r.json()
            dates, prices = self._extract_date_prices(data)
            prices_dict[ticker] = prices
            if final_dates is None:
                final_dates = dates
        
        return pd.DataFrame(prices_dict, index=pd.to_datetime(final_dates))
            
    
    def _extract_date_prices(self, ticker_object):
        data = ticker_object.get('Time Series (Daily)')
        dates = list(data.keys())
        prices = [float(value.get('4. close')) for value in data.values()]
        return dates, prices

    def __normalize_data(self, tickers_df: pd.DataFrame) -> pd.DataFrame:
        shifted_df = tickers_df.shift(periods=-1)
        return (tickers_df - shifted_df) / shifted_df
    
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
            budget_allocation=allocation_budget if allocation_budget else {}
        )
        


if __name__ == '__main__':
    optimizer = PortfolioOptimizer(['NVDA', 'GOOGL', 'AAPL'])
    result  = optimizer.return_highest_sharpe_ratio(budget = Decimal('10000'))
    print(result)
