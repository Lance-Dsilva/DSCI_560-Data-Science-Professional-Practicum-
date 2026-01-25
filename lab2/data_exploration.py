import os
import re
import json
import shutil
import time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter

# Scraping & Extraction
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from readability import Document
import html2text
import kagglehub
import pdfplumber

# --- CONFIGURATION ---
DATA_DIR = "training_data"
os.makedirs(DATA_DIR, exist_ok=True)

# ---------------------------------------------------------
# 1. DATA ACQUISITION: KAGGLE & WEB
# ---------------------------------------------------------

def run_kaggle_step():
    print("\n[1/4] Downloading Kaggle Dataset...")
    try:
        cache_path = kagglehub.dataset_download("swaptr/layoffs-2022")
        source_file = os.path.join(cache_path, "layoffs.csv")
        dest_file = os.path.join(DATA_DIR, "layoffs.csv")
        shutil.copy(source_file, dest_file)
        print(f" CSV saved to: {dest_file}")
    except Exception as e:
        print(f" Kaggle Error: {e}")

def run_scraper_step():
    print("\n[2/4] Scraping Dynamic Web Content...")
    urls = [
        "https://www.adpresearch.com/yes-ai-is-affecting-employment-heres-the-data/",
        "https://news.crunchbase.com/startups/tech-layoffs/",
        "https://mitsloan.mit.edu/ideas-made-to-matter/how-artificial-intelligence-impacts-us-labor-market",
        "https://budgetlab.yale.edu/research/evaluating-impact-ai-labor-market-current-state-affairs"
    ]
    
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    h = html2text.HTML2Text()
    h.ignore_links = True
    h.body_width = 0

    for url in urls:
        try:
            print(f"🔍 Processing: {url}")
            driver.get(url)
            time.sleep(3) # Allow JS to settle
            
            doc = Document(driver.page_source)
            title = doc.title()
            clean_md = h.handle(doc.summary())
            
            safe_name = re.sub(r'\W+', '_', title)[:50] + ".txt"
            with open(os.path.join(DATA_DIR, safe_name), "w", encoding="utf-8") as f:
                f.write(f"TITLE: {title}\nURL: {url}\n\n{clean_md}")
            print(f" Extracted: {safe_name}")
        except Exception as e:
            print(f" Scraping Failed for {url}: {e}")
    driver.quit()

# ---------------------------------------------------------
# 2. THE ANALYSIS ENGINE (DEEP DIVE)
# ---------------------------------------------------------

def run_analysis_step():
    print("\n[3/4]  Launching Deep Data Analysis...")
    
    # --- A. STRUCTURED DATA ANALYSIS (CSV) ---
    csv_path = os.path.join(DATA_DIR, "layoffs.csv")
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        
        # --- NEW: PREVIEW CSV DATA ---
        print("\n---  CSV Data Preview (Top 10 Rows) ---")
        print(df.head(10)) 
        print("-" * 40)
        
        print("\n--- CSV Metrics ---")
        # 1. Basic Dimensions
        print(f"Records: {df.shape[0]} | Features: {df.shape[1]}")
        
        # 2. Outlier Detection
        if 'total_laid_off' in df.columns:
            mean = df['total_laid_off'].mean()
            std = df['total_laid_off'].std()
            outliers = df[df['total_laid_off'] > (mean + 3 * std)]
            print(f"Extreme Layoff Events Detected: {len(outliers)}")

        # 3. Categorical Distribution
        plt.figure(figsize=(12, 6))
        sns.countplot(data=df, y='industry', order=df['industry'].value_counts().index[:10])
        plt.title("Top 10 Affected Industries")
        plt.show()

        # 4. Correlation Heatmap
        plt.figure(figsize=(8, 6))
        numeric_df = df.select_dtypes(include=[np.number])
        sns.heatmap(numeric_df.corr(), annot=True, cmap='viridis')
        plt.title("Feature Correlation")
        plt.show()

    # --- B. UNSTRUCTURED TEXT ANALYSIS (NLP) ---
    print("\n--- Text Corpus Linguistics ---")
    text_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.txt')]
    all_content = ""
    text_stats = []

    for tf in text_files:
        with open(os.path.join(DATA_DIR, tf), 'r', encoding='utf-8') as f:
            raw = f.read()
            all_content += raw.lower()
            
            sentences = re.split(r'[.!?]+', raw)
            words = re.findall(r'\w+', raw.lower())
            
            avg_sentence_len = len(words) / len(sentences) if len(sentences) > 0 else 0
            lexical_diversity = len(set(words)) / len(words) if len(words) > 0 else 0
            
            text_stats.append({
                "file": tf,
                "word_count": len(words),
                "lexical_richness": round(lexical_diversity, 3),
                "avg_sentence_complexity": round(avg_sentence_len, 2)
            })

    stats_df = pd.DataFrame(text_stats)
    print(stats_df.to_string(index=False))

    # 5. Keyword Density
    keywords = ['ai', 'intelligence', 'automation', 'layoffs', 'jobs', 'labor', 'growth']
    tokens = re.findall(r'\w+', all_content)
    counts = Counter(tokens)
    
    print("\nTargeted Keyword Density:")
    for k in keywords:
        print(f"- '{k}': {counts[k]} occurrences")

    # 6. Global Themes Chart
    stop_words = {'the', 'and', 'for', 'that', 'with', 'from', 'this', 'were', 'have'}
    filtered_tokens = [t for t in tokens if t not in stop_words and len(t) > 3]
    top_tokens = Counter(filtered_tokens).most_common(10)
    
    plt.figure(figsize=(10, 4))
    words, freqs = zip(*top_tokens)
    plt.bar(words, freqs, color='skyblue')
    plt.title("Top Content Themes")
    plt.show()

# ---------------------------------------------------------
# 3. PDF RECONSTRUCTION LOGIC
# ---------------------------------------------------------

def process_pdfs_in_folder():
    print("\n[4/4]  Checking for PDFs...")
    pdf_files = [f for f in os.listdir(".") if f.endswith(".pdf")]
    
    if not pdf_files:
        print("No local PDFs found to reconstruct.")
        return

    for pdf_name in pdf_files:
        print(f" Reconstructing: {pdf_name}")
        with pdfplumber.open(pdf_name) as pdf:
            full_text = ""
            for page in pdf.pages:
                text = page.extract_text()
                if text: full_text += text + "\n"
            
            out_name = pdf_name.replace(".pdf", "_reconstructed.txt")
            with open(os.path.join(DATA_DIR, out_name), "w") as f:
                f.write(full_text)
        print(f"PDF converted to text.")

# ---------------------------------------------------------
# EXECUTION
# ---------------------------------------------------------

if __name__ == "__main__":
    start_time = time.time()
    print(" STARTING A PIPELINE")
    
    run_kaggle_step()
    run_scraper_step()
    process_pdfs_in_folder()
    run_analysis_step()
    
    elapsed = round(time.time() - start_time, 2)
    print(f"\n PIPELINE COMPLETE in {elapsed}s")