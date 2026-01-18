import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


url = "https://www.cnbc.com/world/?region=world"

file_path = "..data/raw_data/web_data.html"


# Set up Chrome options for headless browsing
chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--disable-gpu') # Added for better compatibility
chrome_options.add_argument('--window-size=1920x1080') # Added for consistent rendering


# Set the binary location for google-chrome-stable
chrome_options.binary_location = '/usr/bin/google-chrome'


# Initialize the Chrome WebDriver
print("Initializing Chrome WebDriver...")
driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)


try:
   # Navigate to the URL
   print(f"Navigating to {url}")
   driver.get(url)


   # Implement an explicit wait for a key element to ensure dynamic content has loaded
   print("Waiting for dynamic content to load...")
   WebDriverWait(driver, 20).until(
       EC.presence_of_element_located((By.CLASS_NAME, 'LatestNews-item'))
   )
   print("Dynamic content loaded.")


   # Get the page source 
   html_content = driver.page_source


   # Save the html_content to the file_path
   directory = os.path.dirname(file_path)
   if directory:
       os.makedirs(directory, exist_ok=True)


   with open(file_path, "w", encoding="utf-8") as f:
       f.write(html_content)


   print(f"Successfully saved dynamic HTML content to {file_path}")


except Exception as e:
   print(f"An error occurred: {e}")
finally:
   # Quit the browser
   driver.quit()
   print("Browser closed.")
