import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
import time
from dotenv import load_dotenv
import os
load_dotenv()

API_KEY=os.environ.get('PROGRAMMABLE_SEARCH_ENGINE_API_KEY')
CSE_ID=os.environ.get('CUSTOM_SEARCH_ENGINE_ID')
query="India"

url=f"https://www.googleapis.com/customsearch/v1?key={API_KEY}&cx={CSE_ID}&q={query}"
response=requests.get(url)
results=response.json()

driver=webdriver.Chrome()
for item in results.get('items',[]):
    title=item['title']
    link=item['link']
    print(f"Opening : {title} -{link}")
    driver.get(link)
    time.sleep(3)

driver.quit()