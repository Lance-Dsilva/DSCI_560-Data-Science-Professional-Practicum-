import requests
import os
from bs4 import BeautifulSoup

# Target URL
url = "https://www.cnbc.com/world/?region=world"

# Headers to avoid blocking
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}

# File path
file_path = "../data/raw_data/web_data.html"

# Ensure directory exists
os.makedirs(os.path.dirname(file_path), exist_ok=True)

# Send request
response = requests.get(url, headers=headers)

if response.status_code == 200:
    html_content = response.text

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            formatted_html = BeautifulSoup(html_content, "html.parser").prettify()
            f.write(formatted_html)

        print(f"Successfully saved HTML content to {file_path}")

    except IOError as e:
        print(f"Error saving file: {e}")

else:
    print(f"Failed to fetch page. Status code: {response.status_code}")
