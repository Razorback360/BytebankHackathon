import os
import yfinance as yf
from pydantic import BaseModel, Field
from openai import OpenAI
from dotenv import load_dotenv
import json
from enum import StrEnum

load_dotenv(override=True)

class FilterObject(BaseModel):
    filterName:str =  Field(..., description="Name of the filter to apply, e.g., 'PE Ratio', 'Market Cap'")
    filterCategory: str = Field(..., description="Category of the filter, e.g., 'valuation', 'growth'")
    filterValue: str = Field(..., description="Value of the filter, e.g., '15', '100B'")
    operation: str = Field(..., description="Operation to apply, e.g., 'greater than', 'less than'")

class AgentFilterResponse(BaseModel):
    filters: list[FilterObject]

class StockMarket(StrEnum):
    US = "US"
    SA = "SR"

class NLPToFilterAgent:
    def __init__(self) -> None:
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.prompt_path = os.environ.get("FILTER_AGENT_PROMPT_PATH")
        with open(os.environ.get("EXPECTED_FILTER_FIELDS_JSON"), "r") as f:
            self.json_entries = json.load(f)
    
    def _build_prompt(self, nlp_input: str) -> str:
        """
        Reads the template and replaces placeholders with REAL data.
        """
        try:
            with open(self.prompt_path, "r") as file:
                template = file.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Prompt file not found at {self.prompt_path}")
            
        
        return template.replace("{fields}", json.dumps(self.json_entries)).replace("{nlp_input}", nlp_input)

    def filter_stocks(self, nlp_input: str, market: StockMarket= StockMarket.US) -> AgentFilterResponse:
        final_prompt = self._build_prompt(nlp_input)
        
        if market == StockMarket.SA:
            final_prompt = final_prompt + "\nNote: Focus on stocks listed in the Saudi Arabian market, and adjust numbers accordingly."
        
        elif market == StockMarket.US:
            final_prompt = final_prompt + "\nNote: Focus on stocks listed in the US market, and adjust the numbers accordingly."
        response = self.client.beta.chat.completions.parse(
            model=os.environ.get("OPENAI_MODEL", "gpt-4o"),
            messages=[
                {"role": "system", "content": "You are an expert financial analyst."},
                {"role": "user", "content": final_prompt}
            ],
            response_format=AgentFilterResponse
        )
        
        return response.choices[0].message.parsed

if __name__ == "__main__":
    agent = NLPToFilterAgent()
    nlp_input = "Find stocks with a low market cap ."
    result = agent.filter_stocks(nlp_input)
    print(result)