import os
import yfinance as yf
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# --- 1. Define Pydantic Models (The "Shape" of the output) ---
class StockKeyFinancials(BaseModel):
    revenue_yoy_growth: float
    net_income_yoy_growth: float
    p_e_ratio: float
    debt_to_equity: float
    market_cap: float
    beta: float

class SWOTAnalysis(BaseModel):
    strengths: list[str]
    weaknesses: list[str]
    opportunities: list[str]
    threats: list[str]

class StockPeerComparison(BaseModel):
    peer_ticker: str
    p_e_ratio: float
    market_cap: float

class StockTechnicalIndicators(BaseModel):
    moving_average_50d: float
    moving_average_200d: float
    rsi: float

class StockAnalysisResult(BaseModel):
    ticker: str
    stock_name: str
    last_close_price: float
    summary: str
    score: float
    key_financials: StockKeyFinancials
    short_term_outlook: str
    long_term_outlook: str
    swot_analysis: SWOTAnalysis
    peer_comparisons: list[StockPeerComparison]
    technical_indicators: StockTechnicalIndicators

# --- 2. The Logic Class ---
class StockAnalyzer:    
    def __init__(self) -> None:
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.prompt_path = os.environ.get("STOCK_ANALYZER_PROMPT_PATH", "stock_analyzer_prompt.txt")
    
    def fetch_real_data(self, ticker: str) -> dict:
        """
        Fetches live data from Yahoo Finance to inject into the prompt.
        """
        print(f"Fetching live data for {ticker}...")
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # safely get data with defaults to prevent errors if keys are missing
        data = {
            "current_price": info.get("currentPrice"),
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "revenue_growth": info.get("revenueGrowth"),
            "profit_growth": info.get("earningsGrowth"),
            "debt_to_equity": info.get("debtToEquity"),
            "beta": info.get("beta"),
            "50d_avg": info.get("fiftyDayAverage"),
            "200d_avg": info.get("twoHundredDayAverage"),
            "industry": info.get("industry"),
            "sector": info.get("sector"),
            "score": info.get("recommendationMean", 0) * 20,  # Scale to 100
        }
        return data

    def _build_prompt(self, ticker: str, financial_data: dict) -> str:
        """
        Reads the template and replaces placeholders with REAL data.
        """
        try:
            with open(self.prompt_path, "r") as file:
                template = file.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Prompt file not found at {self.prompt_path}")
            
        # Convert dictionary to a string for the AI to read
        context_str = "\n".join([f"{k}: {v}" for k, v in financial_data.items()])
        
        return template.replace("{ticker}", ticker).replace("{financial_context}", context_str)

    def analyze_stock(self, ticker: str) -> StockAnalysisResult:
        # 1. Get the Raw Data
        raw_data = self.fetch_real_data(ticker)
        
        # 2. Construct the Prompt with that data
        final_prompt = self._build_prompt(ticker, raw_data)
        
        # 3. Call OpenAI with Structured Outputs
        print("Analyzing with AI...")
        completion = self.client.beta.chat.completions.parse(
            model="gpt-4o-2024-08-06",  # Must use a model that supports structured outputs
            messages=[
                {"role": "system", "content": "You are a helpful financial analyst assistant."},
                {"role": "user", "content": final_prompt}
            ],
            response_format=StockAnalysisResult,
        )
        
        return completion.choices[0].message.parsed

# --- 3. Execution ---
if __name__ == "__main__":
    analyzer = StockAnalyzer()
    
    # Example: Analyze Apple
    result = analyzer.analyze_stock("AAPL")
    
    # Print readable output
    print("\n" + "="*50)
    print(f"ANALYSIS REPORT: {result.stock_name} ({result.ticker})")
    print("="*50)
    print(f"Price: ${result.last_close_price}")
    print(f"Overall Score: {result.score}/100")
    print(f"\nSummary:\n{result.summary}")
    print(f"\nShort Term Outlook: {result.short_term_outlook}")
    print(f"Long Term Outlook: {result.long_term_outlook}")
    print("\nSWOT Analysis:")
    print(f"  Strengths: {result.swot_analysis.strengths[:2]}")
    print(f"  Threats:   {result.swot_analysis.threats[:2]}")
    print("FULL RESULTS:")
    print(result.model_dump(mode="json"))