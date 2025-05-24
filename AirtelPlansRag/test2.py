import requests
import pandas as pd
API_ENDPOINT = "https://api.webscraper.io/api/v1/sitemap?api_token=c1d7qu46x5oMvidXr8TFkB5Pv1c1Istr0pQjTlBP8D0xCfU2swJqDf6C5Jxb"  # e.g., "https://api.webscraper.io/v1"
API_TOKEN = "c1d7qu46x5oMvidXr8TFkB5Pv1c1Istr0pQjTlBP8D0xCfU2swJqDf6C5Jxb"
TARGET_URL = "https://www.airtel.in/recharge-plans"
params = {
    "api_key": API_TOKEN,
    "url": TARGET_URL,
    "render_js": 1,  
    "extract_rules": {
        "plans": {
            "type": "list",
            "selector": ".pack-card-container",  
            "output": {
                "price": ".pack-card-heading",
                "data": ".pack-card-detail:nth-of-type(1)",
                "validity": ".pack-card-detail:nth-of-type(2)",
                "benefits": ".pack-card-benefits"
            }
        }
    }
}
response = requests.get(API_ENDPOINT, params=params)
data = response.json()
plans = data.get("plans", [])
df = pd.DataFrame(plans)
df.to_csv("airtel_plans.csv", index=False)
print(df)