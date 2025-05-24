from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from bs4 import BeautifulSoup
import time
import json
import re 

AIRTEL_RECHARGE_URL = "https://www.airtel.in/recharge-online"
CHROMEDRIVER_PATH = None 
ACTION_DELAY = 3 
PLAN_TYPES = [
    "Data",
    "International Roaming",
    "Truly Unlimited",
    "Talktime (top up voucher)", # Using the exact name from the screenshot
    "Inflight Roaming packs",
    "Plan vouchers"
]
PLAN_CARD_WRAPPER_CLASS = 'packs-card-content'
PLAN_DETAIL_CLASS = 'pack-card-detail'
HEADING_CLASS = 'pack-card-heading'
SUB_HEADING_CLASS = 'pack-card-sub-heading'
BENEFITS_HEADING_CLASS = 'pack-card-benefits-heading'
BENEFITS_CONTENT_ELEMENTS = ['div', 'span', 'p'] # Common tags for content


# --- WebDriver Setup ---
options = webdriver.ChromeOptions()
options.add_argument("--headless")           # Run in headless mode (no browser window)
options.add_argument("--disable-gpu")       # Recommended for headless mode
options.add_argument("--no-sandbox")        # Recommended for headless mode (important in containers/CI)
options.add_argument("start-maximized")     # Optional: Start browser maximized
options.add_argument("--disable-infobars")  # Disables "Chrome is being controlled by automated test software" bar
options.add_argument("--disable-dev-shm-usage") # Fixes issues with /dev/shm in Linux/Docker
options.add_argument("--disable-browser-side-navigation") # Can help with flaky element errors
options.add_argument(f"user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36") # Realistic User-Agent

# Initialize WebDriver
if CHROMEDRIVER_PATH:
    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=options)
else:
    driver = webdriver.Chrome(options=options)

# --- Global Data Storage ---
# Stores plans categorized by their type (e.g., {'Data': [plan1, plan2], 'Talktime': [plan3]})
all_plans_by_type = {}

# --- Function to Extract Plan Data from HTML ---
def extract_plans_data(html_content, plan_type_name, source_url):
    soup = BeautifulSoup(html_content, 'html.parser')
    current_page_plans = []

    # Find all individual plan card containers using the confirmed class
    plan_cards = soup.find_all('div', class_=PLAN_CARD_WRAPPER_CLASS)

    if not plan_cards:
        print(f"WARNING: No plan cards found for '{plan_type_name}' with class '{PLAN_CARD_WRAPPER_CLASS}'.")
        return current_page_plans

    print(f"Found {len(plan_cards)} potential plan cards for '{plan_type_name}'.")
    for i, card in enumerate(plan_cards):
        plan_info = {
            'plan_type': plan_type_name,
            'source_url': source_url,
            'name': 'N/A', # Placeholder for plan name
            'price': 'N/A',
            'data': 'N/A',
            'validity': 'N/A',
            'calls': 'N/A',
            'sms': 'N/A',
            'ott_benefits': 'None',
            'other_details': [] # To catch any other scraped details not explicitly categorized
        }
        try:
            # Plan Name: Based on the screenshot, it's often a prominent heading/text
            # I'll look for an H2/H3 or strong tag within the card, or a general text area.
            # You might need to refine this if a specific name is missing or incorrect.
            # Let's try finding the text in the 'pack-card-left-section' first, as it's a prominent wrapper.
            left_section = card.find('div', class_='pack-card-left-section')
            if left_section:
                # Look for a heading or the first strong text that looks like a name
                name_el = left_section.find(['h2', 'h3', 'strong', 'span'], class_=re.compile(r'plan-name|pack-title|recharge-name|product-name|heading|text', re.I))
                if name_el:
                    plan_info['name'] = name_el.text.strip()
                else: # Fallback: Sometimes the first prominent text is the name
                    first_text_el = left_section.find(text=True)
                    if first_text_el and first_text_el.strip():
                        plan_info['name'] = first_text_el.strip()

            # Extract details using the 'pack-card-detail' structure
            detail_sections = card.find_all('div', class_=PLAN_DETAIL_CLASS)

            for detail_section in detail_sections:
                heading_el = detail_section.find('div', class_=HEADING_CLASS)
                sub_heading_el = detail_section.find('div', class_=SUB_HEADING_CLASS)

                heading_text = heading_el.text.strip() if heading_el else ''
                sub_heading_text = sub_heading_el.text.strip().lower() if sub_heading_el else ''

                # Logic to classify details based on keywords
                if '₹' in heading_text or 'rs.' in heading_text.lower():
                    plan_info['price'] = heading_text
                elif 'gb' in heading_text.lower() or 'mb' in heading_text.lower() or 'data' in sub_heading_text:
                    plan_info['data'] = heading_text
                elif 'day' in heading_text.lower() or 'days' in heading_text.lower() or 'validity' in sub_heading_text:
                    plan_info['validity'] = heading_text
                elif 'calls' in sub_heading_text or 'unlimited' in heading_text.lower() and 'calls' not in plan_info['calls'].lower():
                    plan_info['calls'] = heading_text
                elif 'sms' in sub_heading_text:
                    plan_info['sms'] = heading_text
                else:
                    # Catch all other details not specifically categorized
                    combined_text = f"{heading_text} {sub_heading_text}".strip()
                    if combined_text:
                        plan_info['other_details'].append(combined_text)

            # Extract OTT Benefits
            # The screenshot shows 'Additional Benefit(s)' followed by what might be an icon and "+1 More".
            # The actual benefits might be in an adjacent element or require clicking "+1 More".
            # For now, we'll try to extract visible text linked to benefits.
            benefits_heading_el = card.find('div', class_=BENEFITS_HEADING_CLASS)
            if benefits_heading_el:
                # Look for common elements right after the benefits heading
                benefits_text_els = benefits_heading_el.find_next_siblings(BENEFITS_CONTENT_ELEMENTS)
                benefits_text = []
                for el in benefits_text_els:
                    if el.text.strip() and '+1 More' not in el.text.strip(): # Avoid "more" links themselves
                        benefits_text.append(el.text.strip())
                
                # Check for a specific benefits container if found in deeper inspection
                benefits_container_el = card.find('div', class_='pack-card-benefits') # As guessed before
                if benefits_container_el:
                    benefits_text.append(benefits_container_el.text.strip())

                if benefits_text:
                    plan_info['ott_benefits'] = ", ".join(list(set(benefits_text))) # Use set to remove duplicates
                else:
                    # If nothing specific found, capture the heading text itself or note
                    plan_info['ott_benefits'] = benefits_heading_el.text.strip() if benefits_heading_el.text.strip() else 'None'
                    if '+1 More' in benefits_heading_el.text:
                         plan_info['ott_benefits'] += " (Click 'View Detail' for full benefits)"


            current_page_plans.append(plan_info)

        except Exception as e:
            print(f"Error processing plan card {i+1} for '{plan_type_name}' on {source_url}: {e}")
            # print(f"Problematic card HTML snippet:\n{card.prettify()[:1000]}") # Uncomment for debugging
            continue # Continue to the next plan card

    return current_page_plans

# --- Main Scraping Logic ---
try:
    print(f"Navigating to: {AIRTEL_RECHARGE_URL}")
    driver.get(AIRTEL_RECHARGE_URL)

    # Initial wait for the main page body to load
    print("Waiting for initial page content to load...")
    WebDriverWait(driver, 30).until( # Increased wait time for robustness
        EC.presence_of_element_located((By.TAG_NAME, 'body'))
    )
    time.sleep(ACTION_DELAY) # Give extra time for dynamic elements to render

    # Loop through each plan type
    for plan_type_name in PLAN_TYPES:
        print(f"\n--- Processing Plan Type: {plan_type_name} ---")
        try:
            # Locate the tab/button for the current plan type.
            # Based on your image, these are likely div/a elements with data-tab-name or specific text/class.
            # We'll prioritize data-tab-name, then try text directly.
            tab_element_locator = (
                By.XPATH,
                f"//div[@data-tab-name='{plan_type_name}'] | " # Try div with data-tab-name
                f"//a[@data-tab-name='{plan_type_name}'] | " # Try a with data-tab-name
                f"//div[contains(@class, 'tab-') and normalize-space(text())='{plan_type_name}'] | " # Try div with tab-like class and exact text
                f"//a[contains(@class, 'tab-') and normalize-space(text())='{plan_type_name}']" # Try a with tab-like class and exact text
            )

            # Wait for the tab element to be clickable
            plan_type_tab = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable(tab_element_locator)
            )
            plan_type_tab.click()
            print(f"Clicked on tab for '{plan_type_name}'.")

            # After clicking, wait for the content specific to this tab to load.
            # We wait for the 'tabs-single-content' div to show the correct 'data-tab-name'.
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, f"//div[@class='tabs-single-content' and @data-tab-name='{plan_type_name}']"))
            )
            # Also wait for at least one plan card to appear to confirm content loaded
            WebDriverWait(driver, 15).until(
                 EC.presence_of_element_located((By.CLASS_NAME, PLAN_CARD_WRAPPER_CLASS))
            )
            time.sleep(ACTION_DELAY) # Give it a moment to fully render after the wait

            # Get the HTML source of the *current* page (after tab content has loaded)
            current_page_html = driver.page_source

            # Extract plans for this specific plan type
            extracted_plans = extract_plans_data(current_page_html, plan_type_name, driver.current_url)
            all_plans_by_type[plan_type_name] = extracted_plans
            print(f"Extracted {len(extracted_plans)} plans for '{plan_type_name}'.")

        except TimeoutException:
            print(f"Timeout: Could not find or click tab for '{plan_type_name}' or content did not load after clicking.")
            all_plans_by_type[plan_type_name] = [] # Record as empty if failed
        except NoSuchElementException:
            print(f"Element not found: Tab for '{plan_type_name}' not found with specified selectors.")
            all_plans_by_type[plan_type_name] = []
        except WebDriverException as e:
            print(f"WebDriver error for tab '{plan_type_name}': {e}. Skipping.")
            all_plans_by_type[plan_type_name] = []
        except Exception as e:
            print(f"An unexpected error occurred while processing '{plan_type_name}': {e}")
            all_plans_by_type[plan_type_name] = []

finally:
    if 'driver' in locals() and driver is not None:
        driver.quit()
        print('\nBrowser closed.')

# --- Final Data Processing and Saving ---
print("\n--- Scraping Complete ---")

total_plans = sum(len(plans) for plans in all_plans_by_type.values())
print(f"Total plans extracted across all categories: {total_plans}")

output_filename = 'airtel_plans_by_type_final.json'
with open(output_filename, 'w', encoding='utf-8') as f:
    json.dump(all_plans_by_type, f, ensure_ascii=False, indent=4)
print(f"\nAll extracted plan data saved to {output_filename}")