# API Request Examples

## Screen Endpoint - POST /screen

### Using cURL

```bash
# Example 1: Screen US stocks with natural language query
curl -X POST "http://localhost:8000/screen" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Find tech companies with market cap greater than 1 billion",
    "market": "US"
  }'

# Example 2: Screen Saudi Arabian stocks
curl -X POST "http://localhost:8000/screen" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Show me energy stocks with PE ratio less than 15",
    "market": "SR"
  }'

# Example 3: Complex query
curl -X POST "http://localhost:8000/screen" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Find companies with revenue growth above 10% and profit margin greater than 5%",
    "market": "US"
  }'
```

### Using Python (requests library)

```python
import requests
import json

# API endpoint
url = "http://localhost:8000/screen"

# Request payload
payload = {
    "query": "Find tech companies with market cap greater than 1 billion",
    "market": "US"
}

# Make POST request
response = requests.post(url, json=payload)

# Check response
if response.status_code == 200:
    tickers = response.json()
    print(f"Found {len(tickers)} stocks:")
    print(tickers)
else:
    print(f"Error: {response.status_code}")
    print(response.json())
```

### Using JavaScript (fetch)

```javascript
// API endpoint
const url = "http://localhost:8000/screen";

// Request payload
const payload = {
    query: "Find tech companies with market cap greater than 1 billion",
    market: "US"
};

// Make POST request
fetch(url, {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload)
})
.then(response => response.json())
.then(data => {
    console.log('Success:', data);
    console.log(`Found ${data.length} stocks:`, data);
})
.catch((error) => {
    console.error('Error:', error);
});
```

### Using Postman

1. **Method**: POST
2. **URL**: `http://localhost:8000/screen`
3. **Headers**:
   - Key: `Content-Type`
   - Value: `application/json`
4. **Body** (raw JSON):
```json
{
    "query": "Find tech companies with market cap greater than 1 billion",
    "market": "US"
}
```

### Request Schema

```json
{
    "query": "string (required) - Natural language description of the stocks you want to find",
    "market": "string (optional, default: 'US') - Either 'US' or 'SR' for Saudi Arabia"
}
```

### Response Schema

```json
[
    "AAPL",
    "MSFT",
    "GOOGL",
    ...
]
```

Returns an array of stock ticker symbols that match your query.

### Example Queries

- "Find companies with high dividend yield"
- "Show me growth stocks with low PE ratio"
- "Find tech companies with revenue greater than 10 billion"
- "Show me stocks with market cap between 1 billion and 10 billion"
- "Find energy companies with positive earnings growth"

