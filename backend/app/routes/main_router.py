from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
from decimal import Decimal
import yfinance as yf
from yfinance import EquityQuery
import io
import asyncio

# Import your custom classes
# Adjust imports based on your actual directory structure
import sys
from pathlib import Path

# Add the parent directory to the path so we can import from agents, optimizers, etc.
backend_dir = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))
from agents.nlp_to_filter_agent import StockMarket
from agents.nlp_to_filter_agent import NLPToFilterAgent, StockMarket as FilterMarket, FilterObject
from agents.stock_analyzer import StockAnalyzer, StockMarket as AnalyzerMarket, StockAnalysisResult
from optimizers.allocation_optimizer import PortfolioOptimizer, StockMarket as OptimizerMarket
from file_generator.pdf_generator import PDFReportGenerator

router = APIRouter()

# --- Request Models ---

class ScreenerRequest(BaseModel):
    query: str
    market: StockMarket = StockMarket.US  # "US" or "SR"

class OptimizerRequest(BaseModel):
    tickers: List[str]
    market: StockMarket = StockMarket.US
    budget: float = 10000.0

class AnalysisRequest(BaseModel):
    ticker: str
    market: StockMarket = StockMarket.US

class PDFRequest(BaseModel):
    ticker: str
    market: StockMarket = StockMarket.US

class StockMetaData(BaseModel):
    symbol: str
    company: str
    sector: str
    price: Decimal
    change: Decimal
    p_e: Decimal
    cap: Decimal

class ScreenerResponse(BaseModel):
    data: list[StockMetaData]
    sqlQuery: str

# --- Helper to resolve Market Enums ---
# Since different files defined their own Enums, we map string to the specific Enum needed
def get_market_enum(market_str: str, enum_cls) -> StockMarket:
    market_str = market_str.upper()
    if market_str == "US":
        return enum_cls.US
    elif market_str == "SR":
        return enum_cls.SA # Note: Analyzer/Filter use 'SA', Optimizer uses 'SA' logic but checks enum value
    else:
        raise HTTPException(status_code=400, detail="Market must be 'US' or 'SR'")

# --- Helper to map operation descriptions to EquityQuery symbols ---
OPERATION_MAP = {
    "equals": "eq",
    "greater than": "gt",
    "less than": "lt",
    "greater than or equal to": "gte",
    "less than or equal to": "lte",
    "is in list": "is-in",
    "between two values": "btwn",
}

def get_operation_symbol(operation_desc: str) -> str:
    """Convert operation description to EquityQuery symbol."""
    operation_lower = operation_desc.lower().strip()
    if operation_lower in OPERATION_MAP:
        return OPERATION_MAP[operation_lower]
    # Try partial matching for flexibility
    for desc, symbol in OPERATION_MAP.items():
        if desc in operation_lower or operation_lower in desc:
            return symbol
    # Default to 'eq' if no match found
    return "eq"

def parse_filter_value(value: str):
    """Parse filter value to appropriate type (number or string)."""
    try:
        # Try to parse as float
        if '.' in value:
            return float(value)
        return int(value)
    except ValueError:
        # Return as string if not a number
        return value

def build_equity_query(filters: List[FilterObject], market: str) -> EquityQuery:
    """
    Convert a list of FilterObject to a yfinance EquityQuery.
    
    Example output:
    EquityQuery('and', [
        EquityQuery('is-in', ['exchange', 'NMS', 'NYQ']),
        EquityQuery('lt', ["epsgrowth.lasttwelvemonths", 15])
    ])
    """
    query_parts = []
    
    # Add market-specific exchange filter
    if market.upper() == "US":
        query_parts.append(EquityQuery('is-in', ['exchange', 'NMS', 'NYQ']))
    elif market.upper() == "SR":
        query_parts.append(EquityQuery('eq', ['exchange', 'SAU']))
    
    # Convert each filter to an EquityQuery
    for f in filters:
        # Remove category prefix (e.g., "price.intradaymarketcap" -> "intradaymarketcap")
        field_name = f.get("filterName")
        
        # Skip exchange filters - we already hardcode them based on market
        if field_name.lower() == 'exchange':
            continue
        
        op_symbol = get_operation_symbol(f.get("operation"))
        value = parse_filter_value(f.get("filterValue"))
        
        if op_symbol == "btwn":
            # Between requires two values - assume comma-separated
            values = [parse_filter_value(v.strip()) for v in f.get("filterValue").split(',')]
            if len(values) == 2:
                query_parts.append(EquityQuery(op_symbol, [field_name, values[0], values[1]]))
        elif op_symbol == "is-in":
            # Is-in requires a list of values
            values = [v.strip() for v in f.get("filterValue").split(',')]
            query_parts.append(EquityQuery(op_symbol, [field_name] + values))
        else:
            # Standard comparison operators
            query_parts.append(EquityQuery(op_symbol, [field_name, value]))
    
    # If only one filter (including exchange), return it directly
    if len(query_parts) == 1:
        return query_parts[0]
    print("Query Parts:", query_parts)
    # Combine all filters with AND
    return EquityQuery('and', query_parts)

def get_stock_metadata(ticker_symbol: str) -> StockMetaData:
    """
    Fetches stock metadata for a given ticker symbol using yfinance.
    """
    try:
        ticker = yf.Ticker(ticker_symbol)
        
        # .fast_info is often faster/more reliable for price data than .info
        current_price = ticker.fast_info.last_price
        previous_close = ticker.fast_info.previous_close
        
        # .info dictionary contains the metadata
        info = ticker.info
        
        # Calculate change (Price - Prev Close)
        if current_price and previous_close:
            price_change = current_price - previous_close
        else:
            price_change = 0.0

        # Helper to safely convert float/None to Decimal
        def to_decimal(value, default=0.0):
            if value is None:
                return Decimal(str(default))
            # Convert to string first to avoid floating point arithmetic artifacts
            return Decimal(str(value))

        return StockMetaData(
            symbol=info.get('symbol', ticker_symbol.upper()),
            company=info.get('shortName', 'Unknown Company'),
            sector=info.get('sector', 'Unknown Sector'),
            
            # fast_info provides floats, convert to Decimal
            price=to_decimal(current_price).quantize(Decimal("0.01")),
            change=to_decimal(price_change).quantize(Decimal("0.01")),
            
            # info['trailingPE'] can be None for unprofitable companies
            p_e=to_decimal(info.get('trailingPE'), default=0.0).quantize(Decimal("0.01")),
            # Market Cap is usually a large integer/float
            cap=to_decimal(info.get('marketCap'), default=0.0).quantize(Decimal("1.00"))
        )

    except Exception as e:
        # In a real app, you might raise a custom HTTP exception or log this
        print(f"Error fetching data for {ticker_symbol}: {e}")
        # Return empty/zeroed object or re-raise
        raise e    

# --- 1. Screener Endpoint ---
@router.post("/screen", response_model=List[str])
async def screen_stocks(request: ScreenerRequest):
    """
    Takes natural language query -> Agents parse filters -> Returns Tickers.
    """
    try:
        # 1. Initialize Agent
        agent = NLPToFilterAgent()
        market_enum = get_market_enum(request.market, StockMarket)
        
        # 2. Get Filter Criteria from NLP
        filter_response = agent.filter_stocks(request.query, market=market_enum)
        
        print(f"Parsed Filters: {filter_response.get("filters")}")
        
        # 3. Build EquityQuery from filters
        equity_query = build_equity_query(filter_response.get("filters"), request.market)
        
        print(f"EquityQuery: {equity_query}")
        
        # 4. Execute the screener query
        screener = yf.screen(equity_query, count=250)
        result = screener
        print(f"Screener Result: {result}")
        
        # 5. Extract tickers from the result
        if result and 'quotes' in result:
            symbols = [quote['symbol'] for quote in result['quotes']]
            
            # Use a Semaphore to limit concurrency to 250 (as requested)
            # This prevents opening too many sockets at once if the list grows
            sem = asyncio.Semaphore(250)

            async def fetch_stock_safe(sym):
                async with sem:
                    # asyncio.to_thread runs the synchronous yfinance code in a separate thread
                    # preventing it from blocking the main event loop
                    try:
                        return await asyncio.to_thread(get_stock_metadata, sym)
                    except Exception as e:
                        print(f"Failed to fetch {sym}: {e}")
                        return None

            # Launch all tasks simultaneously
            tasks = [fetch_stock_safe(sym) for sym in symbols]
            
            # gather waits for all to complete
            results = await asyncio.gather(*tasks)
            
            # Filter out any failures (None values)
            tickers = [r for r in results if r is not None]
        else:
            tickers = []
        # te
        print("i love u")
        return ScreenerResponse(
            data=tickers,
            sqlQuery= filter_response.get("sqlQuery")
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# --- 2. Optimizer Endpoint ---
@router.post("/optimize")
async def optimize_portfolio(request: OptimizerRequest):
    """
    Takes list of tickers -> Returns optimized allocation (Sharpe Ratio).
    """
    try:
        # 1. Resolve Market Enum
        market_enum = get_market_enum(request.market, StockMarket)
        
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
        market_enum = get_market_enum(request.market, StockMarket)
        
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
        market_enum = get_market_enum(request.market, StockMarket)
        
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