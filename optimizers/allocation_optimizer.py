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
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv(override=True)
logger.info("Environment variables loaded")

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
        try:
            logger.info(f"Initializing PortfolioOptimizer with tickers={tickers}, market={stock_market}")
            self.tickers = tickers
            self.stock_market = stock_market
            self.dates = None
            
            logger.debug("Extracting historical data...")
            tickers_df = self.__extract_data()
            logger.debug(f"Data shape after extraction: {tickers_df.shape}")
            
            logger.debug("Normalizing data...")
            self.normalized_df = self.__normalize_data(tickers_df)
            logger.debug(f"Normalized data shape: {self.normalized_df.shape}")
            
            self.mean_returns = np.array([self.normalized_df.mean()[ticker] for ticker in self.tickers])
            logger.debug(f"Mean returns: {self.mean_returns}")
            
            self.cov = np.array(self.normalized_df.cov())
            logger.debug(f"Covariance matrix shape: {self.cov.shape}")
            
            self.n = len(self.tickers)
            logger.info(f"PortfolioOptimizer initialized successfully with {self.n} tickers")
        except Exception as e:
            logger.error(f"Error during initialization: {str(e)}", exc_info=True)
            raise

    
    def __extract_data(self) -> pd.DataFrame:
        """
        Fetches historical data using yfinance.
        - market: StockMarket Enum (US or SA).
        """
        try:
            logger.debug(f"Starting data extraction for market: {self.stock_market}")
            
            # 1. Adjust tickers based on the selected market
            formatted_tickers = []
            for ticker in self.tickers:
                if self.stock_market == StockMarket.SA:
                    # Append suffix for Saudi market (e.g., 1120 -> 1120.SR)
                    formatted_ticker = f"{ticker}.{self.stock_market.value}"
                    formatted_tickers.append(formatted_ticker)
                    logger.debug(f"Formatted ticker {ticker} to {formatted_ticker} for Saudi market")
                else:
                    # Default for US (no suffix needed usually)
                    formatted_tickers.append(ticker)
                    logger.debug(f"Using ticker {ticker} for US market")

            logger.info(f"Downloading data for: {formatted_tickers}")
            
            # 2. Download data in batch (more efficient than looping)
            # using 'auto_adjust=True' gets the Adjusted Close directly as 'Close'
            data = yf.download(formatted_tickers, period="1y", auto_adjust=True, progress=False)
            logger.debug(f"Downloaded data shape: {data.shape}")

            if len(self.tickers) == 1:
                logger.debug("Single ticker detected, restructuring data")
                prices_df = pd.DataFrame(data['Close'])
                prices_df.columns = self.tickers
            else:
                prices_df = data['Close']
                logger.debug(f"Multiple tickers detected, columns before rename: {list(prices_df.columns)}")
                
                if self.stock_market == StockMarket.SA:
                    prices_df.columns = [col.replace(f".{self.stock_market.value}", "") for col in prices_df.columns]
                    logger.debug(f"Columns after rename: {list(prices_df.columns)}")

            # Ensure no missing data (forward fill then drop remaining)
            prices_df = prices_df.ffill().dropna()
            logger.info(f"Data extraction complete. Final shape: {prices_df.shape}, Missing values: {prices_df.isnull().sum().sum()}")
            return prices_df
        except Exception as e:
            logger.error(f"Error during data extraction: {str(e)}", exc_info=True)
            raise

    def __normalize_data(self, tickers_df: pd.DataFrame) -> pd.DataFrame:
        try:
            logger.debug(f"Normalizing data with shape: {tickers_df.shape}")
            normalized = tickers_df.pct_change().dropna()
            logger.debug(f"Normalized data shape: {normalized.shape}")
            logger.debug(f"Normalized data statistics:\n{normalized.describe()}")
            return normalized
        except Exception as e:
            logger.error(f"Error during data normalization: {str(e)}", exc_info=True)
            raise
    
    def _minimize_risks(self, daily_reward, budget: Decimal, allow_short=False):
        """
        Minimize portfolio variance subject to:
        - Expected return = daily_reward
        - Sum of weights = 1
        - Optional: No short selling (w >= 0)
        """
        try:
            logger.debug(f"Minimizing risks for daily_reward={daily_reward}, budget={budget}, allow_short={allow_short}")
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
                logger.debug("Short selling allowed")
            else:
                bounds = [(0, None)] * self.n  # No short selling
                logger.debug("Short selling not allowed")
            
            # Initial guess: equal weights
            w0 = np.ones(self.n) / self.n
            logger.debug(f"Initial weights: {w0}")
            
            # Optimize
            logger.debug("Starting optimization...")
            result = sco.minimize(objective, w0, method='SLSQP', bounds=bounds, constraints=constraints)
            
            if not result.success:
                logger.warning(f"Optimization did not converge. Message: {result.message}")
            else:
                logger.debug(f"Optimization successful")
            
            w = result.x
            logger.debug(f"Optimized weights: {w}")
            
            # Build results
            results = {self.tickers[i]: float(w[i]) * budget for i in range(self.n)}
            results['daily_variance'] = float(w @ self.cov @ w)
            results['daily_return'] = float(self.mean_returns @ w * budget)
            results['daily_std'] = float(np.sqrt(w @ self.cov @ w) * budget)
            results['optimization_success'] = result.success
            
            logger.debug(f"Results: variance={results['daily_variance']}, return={results['daily_return']}, std={results['daily_std']}")
            
            return results
        except Exception as e:
            logger.error(f"Error during risk minimization: {str(e)}", exc_info=True)
            raise
    

    
    def efficient_frontier(self, budget: Decimal, n_points=50, allow_short=False):
        """
        Compute the efficient frontier: optimal portfolios for different return levels
        
        Returns: List of dictionaries with portfolio weights and statistics
        """
        try:
            logger.info(f"Computing efficient frontier with n_points={n_points}, budget={budget}")
            min_return = np.min(self.mean_returns)
            max_return = np.max(self.mean_returns)
            budget = float(budget)
            logger.debug(f"Return range: [{min_return}, {max_return}]")
            
            target_returns = np.linspace(min_return, max_return, n_points)
            frontier = []
            
            for idx, target in enumerate(target_returns):
                try:
                    logger.debug(f"Processing frontier point {idx+1}/{n_points}, target_return={target}")
                    result = self._minimize_risks(target, budget=budget, allow_short=allow_short)
                    if result['optimization_success']:
                        portfolio = {
                            'target_return': target,
                            'variance': result['daily_variance'],
                            'std': np.sqrt(result['daily_variance']),
                            'weights': {k: v/budget if budget > 0 else v 
                                       for k, v in result.items() 
                                       if k in self.tickers}
                        }
                        frontier.append(portfolio)
                        logger.debug(f"Successfully added portfolio to frontier")
                    else:
                        logger.warning(f"Optimization failed for target return {target}")
                except Exception as e:
                    logger.warning(f"Error processing frontier point {idx}: {str(e)}")
                    continue
            
            logger.info(f"Efficient frontier computed with {len(frontier)} successful portfolios")
            return frontier
        except Exception as e:
            logger.error(f"Error computing efficient frontier: {str(e)}", exc_info=True)
            raise
    
    def return_highest_sharpe_ratio(self, budget: Decimal, allow_short=False)->OptimizerResult:
        """
        Find the portfolio with the highest Sharpe ratio
        
        Returns: Dictionary with portfolio weights and statistics
        """
        try:
            logger.info(f"Finding highest Sharpe ratio portfolio with budget={budget}")
            
            ef = self.efficient_frontier(budget=budget, allow_short=allow_short)
            logger.debug(f"Efficient frontier contains {len(ef)} portfolios")
            
            if not ef:
                logger.error("Efficient frontier is empty, cannot find best portfolio")
                raise ValueError("Efficient frontier is empty")
            
            best_portfolio = None
        
            risk_free_rate = 0.03 / 252  # Assuming 3% annual risk-free rate
            logger.debug(f"Risk-free rate (daily): {risk_free_rate}")

            max_sharpe_ratio = -np.inf
            portfolio_index = -1

            for i, portfolio in enumerate(ef):
                try:
                    expected_return = portfolio['target_return']
                    std_dev = portfolio['std']
                    
                    if std_dev == 0:
                        logger.warning(f"Portfolio {i} has zero std_dev, skipping")
                        continue
                    
                    sharpe_ratio = (expected_return - risk_free_rate) / std_dev
                    logger.debug(f"Portfolio {i}: return={expected_return}, std={std_dev}, sharpe={sharpe_ratio}")
                    
                    if sharpe_ratio > max_sharpe_ratio:
                        max_sharpe_ratio = sharpe_ratio
                        portfolio_index = i
                        logger.debug(f"New best Sharpe ratio: {max_sharpe_ratio}")
                except Exception as e:
                    logger.warning(f"Error calculating Sharpe ratio for portfolio {i}: {str(e)}")
                    continue

            best_portfolio = ef[portfolio_index] if portfolio_index >= 0 else None
            
            if best_portfolio is None:
                logger.error("Could not find best portfolio")
                raise ValueError("Could not find best portfolio")
            
            allocation_budget = {k: v * float(budget) for k, v in best_portfolio['weights'].items()} if best_portfolio else None
            
            logger.info(f"Best portfolio found with Sharpe ratio: {max_sharpe_ratio}")
            logger.debug(f"Best portfolio weights: {best_portfolio['weights']}")
            logger.debug(f"Best portfolio allocation: {allocation_budget}")
            
            result = OptimizerResult(
                weights=best_portfolio['weights'] if best_portfolio else {},
                sharpe_ratio=max_sharpe_ratio,
                budget_allocation=allocation_budget if allocation_budget else {},
                target_return=best_portfolio.get("target_return"),
                volatility=best_portfolio.get("daily_variance") * np.sqrt(252)
            )
            
            logger.info(f"Returning OptimizerResult with sharpe_ratio={result.sharpe_ratio}, volatility={result.volatility}")
            return result
        except Exception as e:
            logger.error(f"Error finding highest Sharpe ratio: {str(e)}", exc_info=True)
            raise
        


if __name__ == '__main__':
    try:
        logger.info("="*50)
        logger.info("Starting PortfolioOptimizer main execution")
        logger.info("="*50)
        
        optimizer = PortfolioOptimizer(['GOOGL', 'NVDA', 'AAPL'], StockMarket.US)
        logger.info("PortfolioOptimizer instance created successfully")
        
        result = optimizer.return_highest_sharpe_ratio(budget=Decimal('10000'))
        logger.info("Optimization completed successfully")
        logger.info(f"Result: {result}")
        print(result)
    except Exception as e:
        logger.error(f"Fatal error in main: {str(e)}", exc_info=True)
        raise
