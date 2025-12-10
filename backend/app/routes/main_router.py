from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
from decimal import Decimal
import yfinance as yf
import io

# Import your custom classes
# Adjust imports based on your actual directory structure
from agents.nlp_to_filter_agent import NLPToFilterAgent, StockMarket as FilterMarket
from agents.stock_analyzer import StockAnalyzer, StockMarket as AnalyzerMarket, StockAnalysisResult
from optimizers.allocation_optimizer import PortfolioOptimizer, StockMarket as OptimizerMarket
from file_generator.pdf_generator import PDFReportGenerator

router = APIRouter()

# --- Request Models ---

class ScreenerRequest(BaseModel):
    query: str
    market: str = "US"  # "US" or "SR"

class OptimizerRequest(BaseModel):
    tickers: List[str]
    market: str = "US"
    budget: float = 10000.0

class AnalysisRequest(BaseModel):
    ticker: str
    market: str = "US"

class PDFRequest(BaseModel):
    ticker: str
    market: str = "US"

# --- Helper to resolve Market Enums ---
# Since different files defined their own Enums, we map string to the specific Enum needed
def get_market_enum(market_str: str, enum_cls):
    market_str = market_str.upper()
    if market_str == "US":
        return enum_cls.US
    elif market_str == "SR":
        return enum_cls.SA # Note: Analyzer/Filter use 'SA', Optimizer uses 'SA' logic but checks enum value
    else:
        raise HTTPException(status_code=400, detail="Market must be 'US' or 'SR'")

# --- 1. Screener Endpoint ---
@router.post("/screen", response_model=List[str])
async def screen_stocks(request: ScreenerRequest):
    """
    Takes natural language query -> Agents parse filters -> Returns Tickers.
    """
    try:
        # 1. Initialize Agent
        agent = NLPToFilterAgent()
        market_enum = get_market_enum(request.market, FilterMarket)
        
        # 2. Get Filter Criteria from NLP
        filter_response = agent.filter_stocks(request.query, market=market_enum)
        
        # 3. Apply Filters to fetch Tickers
        # NOTE: The provided code only gives the *criteria* (FilterObject).
        # It does not contain the logic to query a DB or API with those filters.
        # Below is a simulation of what that step would look like.
        
        print(f"Applied Filters: {filter_response.filters}")
        
        # MOCK IMPLEMENTATION FOR DEMONSTRATION
        # In a real app, you would pass 'filter_response.filters' to a screening engine.
        if request.market == "US":
            # Simulation: Returning popular US tech stocks
            return ["AAPL", "NVDA", "GOOGL", "MSFT", "AMZN"] 
        else:
            # Simulation: Returning popular Saudi stocks (Aramco, Al Rajhi, etc.)
            return ["2222", "1120", "2010"]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- 2. Optimizer Endpoint ---
@router.post("/optimize")
async def optimize_portfolio(request: OptimizerRequest):
    """
    Takes list of tickers -> Returns optimized allocation (Sharpe Ratio).
    """
    try:
        # 1. Resolve Market Enum
        market_enum = get_market_enum(request.market, OptimizerMarket)
        
        # 2. Initialize Optimizer
        # Note: This will trigger yfinance downloads
        optimizer = PortfolioOptimizer(tickers=request.tickers, stock_market=market_enum)
        
        # 3. Calculate Result
        result = optimizer.return_highest_sharpe_ratio(budget=Decimal(request.budget))
        
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- 3. Analysis Endpoint ---
@router.post("/analyze", response_model=StockAnalysisResult)
async def analyze_stock(request: AnalysisRequest):
    """
    Takes a single ticker -> Returns AI Analysis (Financials, SWOT, Outlook).
    """
    try:
        market_enum = get_market_enum(request.market, AnalyzerMarket)
        
        analyzer = StockAnalyzer()
        result = analyzer.analyze_stock(request.ticker, market=market_enum)
        
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- 4. PDF Report Endpoint ---
@router.post("/report/pdf")
async def generate_pdf_report(request: PDFRequest):
    """
    Takes a single ticker -> Runs Analysis -> Generates PDF -> Returns File Stream.
    """
    try:
        market_enum = get_market_enum(request.market, AnalyzerMarket)
        
        # 1. Run Analysis
        analyzer = StockAnalyzer()
        analysis_result = analyzer.analyze_stock(request.ticker, market=market_enum)
        
        # 2. Fetch Metadata (Website for Logo)
        # This logic is adapted from your pdf_generator.py main block
        ticker_lookup = request.ticker
        if market_enum == AnalyzerMarket.SA:
            ticker_lookup = f"{request.ticker}.SR"
            
        try:
            stock_info = yf.Ticker(ticker_lookup).info
            website = stock_info.get('website', '')
        except Exception:
            website = ""

        # 3. Generate PDF
        pdf_gen = PDFReportGenerator(analysis_result)
        pdf_buffer = pdf_gen.create_pdf(website_url=website)
        
        # 4. Return as file stream
        filename = f"{analysis_result.ticker}_Analysis.pdf"
        
        return StreamingResponse(
            pdf_buffer, 
            media_type="application/pdf", 
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"PDF Generation failed: {str(e)}")