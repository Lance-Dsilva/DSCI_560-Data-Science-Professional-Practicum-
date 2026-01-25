import os
import csv
from bs4 import BeautifulSoup

# File paths
input_file = "../data/raw_data/web_data.html"
output_dir = "../data/processed_data/"
market_csv = os.path.join(output_dir, "market_data.csv")
news_csv = os.path.join(output_dir, "news_data.csv")

# Create output directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)

market_data = []
news_data = []

print("Reading HTML file...")
with open(input_file, "r", encoding="utf-8") as file:
    soup = BeautifulSoup(file.read(), "html.parser")

# Market Banner
print("Filtering fields: Market Banner")

market_cards = soup.find_all("a", class_="MarketCard-container")
print(f"Found {len(market_cards)} market cards")

for card in market_cards:
    symbol = card.find("span", class_="MarketCard-symbol")
    position = card.find("span", class_="MarketCard-stockPosition")
    change = card.find("span", class_="MarketCard-changesPct")

    market_data.append({
        "marketCard_symbol": symbol.text.strip() if symbol else "N/A",
        "marketCard_stockPosition": position.text.strip() if position else "N/A",
        "marketCard_changePct": change.text.strip() if change else "N/A"
    })

# Latest News
print("Filtering fields: Latest News")

news_items = soup.find_all("li", class_="LatestNews-item")

for item in news_items:
    time = item.find("time", class_="LatestNews-timestamp")
    headline = item.find("a", class_="LatestNews-headline")

    if headline:
        news_data.append({
            "LatestNews-timestamp": time.text.strip() if time else "N/A",
            "title": headline.text.strip(),
            "link": headline.get("href")
        })

print(f"Found {len(news_data)} news items")

# Save Market CSV
print("Storing Market data into CSV...")
with open(market_csv, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "marketCard_symbol",
            "marketCard_stockPosition",
            "marketCard_changePct"
        ]
    )
    writer.writeheader()
    writer.writerows(market_data)

print(f"Market CSV created: {market_csv}")

# Save News CSV
print("Storing News data into CSV...")
with open(news_csv, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "LatestNews-timestamp",
            "title",
            "link"
        ]
    )
    writer.writeheader()
    writer.writerows(news_data)

print(f"News CSV created: {news_csv}")

print("\n--- Data Filtering Complete ---")
