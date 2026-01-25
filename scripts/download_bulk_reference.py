"""
Download bulk reference data files for entity mapping.

Available free sources:
1. GLEIF - LEI data (we have ISIN-LEI)
   - LEI-CDF (full LEI records with parent/ultimate parent)
   - BIC-LEI mappings
   
2. SEC EDGAR
   - company_tickers.json - CIK to ticker/name
   - company_tickers_exchange.json - includes exchange
   - submissions bulk (CIK, name, SIC, addresses)
   
3. OpenFIGI - requires API but has bulk download for registered users

4. ISO data
   - Country codes
   - Currency codes
"""
import os
import json
import gzip
import zipfile
import urllib.request
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).parent.parent / "entityspine_data" / "bulk_reference"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DOWNLOADS = {
    # SEC EDGAR
    "sec_company_tickers": {
        "url": "https://www.sec.gov/files/company_tickers.json",
        "filename": "sec_company_tickers.json",
        "description": "SEC CIK to ticker/name mapping"
    },
    "sec_company_tickers_exchange": {
        "url": "https://www.sec.gov/files/company_tickers_exchange.json",
        "filename": "sec_company_tickers_exchange.json",
        "description": "SEC CIK to ticker/name/exchange mapping"
    },
    
    # GLEIF - BIC to LEI
    "gleif_bic_lei": {
        "url": "https://mapping.gleif.org/api/v2/bic-lei/",
        "filename": "gleif_bic_lei.json",
        "description": "GLEIF BIC-LEI mappings (API endpoint)",
        "api": True
    },
    
    # GLEIF - Full LEI records (Level 1)
    "gleif_lei_full": {
        "url": "https://leidata.gleif.org/api/v1/concatenated-files/lei2/get/",
        "filename": "gleif_lei_full_index.json",
        "description": "GLEIF full LEI data (index only - file is very large)",
        "api": True,
        "skip_download": True  # Just get index, full file is ~4GB
    },
}


def download_file(url, output_path, headers=None):
    """Download a file with progress."""
    if headers is None:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            content_length = resp.headers.get('Content-Length')
            size_str = f" ({int(content_length) / 1024 / 1024:.1f} MB)" if content_length else ""
            print(f"  Downloading{size_str}...")
            
            with open(output_path, 'wb') as f:
                total = 0
                while True:
                    chunk = resp.read(8192 * 16)
                    if not chunk:
                        break
                    f.write(chunk)
                    total += len(chunk)
            
            print(f"  Saved to: {output_path}")
            return True
    except Exception as e:
        print(f"  ERROR: {e}")
        return False


def download_sec_data():
    """Download SEC EDGAR reference files."""
    print("\n" + "=" * 60)
    print("SEC EDGAR Data")
    print("=" * 60)
    
    for key in ["sec_company_tickers", "sec_company_tickers_exchange"]:
        info = DOWNLOADS[key]
        output_path = DATA_DIR / info["filename"]
        
        print(f"\n{info['description']}:")
        
        if output_path.exists():
            print(f"  Already exists: {output_path}")
            # Show sample
            with open(output_path, 'r') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    print(f"  Entries: {len(data):,}")
        else:
            download_file(info["url"], output_path)


def download_gleif_bic_lei():
    """Download GLEIF BIC-LEI mappings."""
    print("\n" + "=" * 60)
    print("GLEIF BIC-LEI Mappings")
    print("=" * 60)
    
    output_dir = DATA_DIR.parent / "gleif"
    output_dir.mkdir(exist_ok=True)
    
    # First get the file list from API
    api_url = "https://mapping.gleif.org/api/v2/bic-lei/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept': 'application/vnd.api+json'
    }
    
    print("Fetching BIC-LEI file list...")
    req = urllib.request.Request(api_url, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            
            if 'data' in data and len(data['data']) > 0:
                latest = data['data'][0]
                file_id = latest['id']
                filename = latest['attributes']['fileName']
                uploaded_at = latest['attributes']['uploadedAt']
                
                print(f"  Latest file: {filename}")
                print(f"  Uploaded: {uploaded_at}")
                
                # Download the file
                download_url = f"https://mapping.gleif.org/api/v2/bic-lei/{file_id}/download"
                output_path = output_dir / filename
                
                if output_path.exists():
                    print(f"  Already exists: {output_path}")
                else:
                    download_file(download_url, output_path, headers={'User-Agent': 'Mozilla/5.0'})
                    
                    # Extract and preview
                    if output_path.suffix == '.zip':
                        print("  Extracting...")
                        with zipfile.ZipFile(output_path, 'r') as zf:
                            for name in zf.namelist():
                                zf.extract(name, output_dir)
                                extracted = output_dir / name
                                print(f"  Extracted: {extracted}")
                                
                                # Count lines
                                with open(extracted, 'r') as f:
                                    lines = sum(1 for _ in f)
                                print(f"  Lines: {lines:,}")
    except Exception as e:
        print(f"  ERROR: {e}")


def download_gleif_lei_index():
    """Get GLEIF LEI data download info."""
    print("\n" + "=" * 60)
    print("GLEIF Full LEI Data (Index)")
    print("=" * 60)
    
    # The golden copy files
    urls_to_try = [
        "https://leidata.gleif.org/api/v1/concatenated-files/lei2/get/",
        "https://goldencopy.gleif.org/api/v2/golden-copies/publishes"
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept': 'application/json'
    }
    
    for url in urls_to_try:
        print(f"\nTrying: {url}")
        req = urllib.request.Request(url, headers=headers)
        
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
                print(f"  Response keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")
                
                # Save the index
                output_path = DATA_DIR / "gleif_lei_index.json"
                with open(output_path, 'w') as f:
                    json.dump(data, f, indent=2)
                print(f"  Saved index to: {output_path}")
                
                # Try to find download URL
                if isinstance(data, dict):
                    if 'data' in data:
                        items = data['data']
                        if isinstance(items, list) and len(items) > 0:
                            latest = items[0]
                            print(f"\n  Latest entry:")
                            print(f"    {json.dumps(latest, indent=4)[:500]}...")
                break
        except Exception as e:
            print(f"  ERROR: {e}")


def analyze_downloaded_data():
    """Analyze downloaded data for entity mapping potential."""
    print("\n" + "=" * 60)
    print("ANALYSIS OF DOWNLOADED DATA")
    print("=" * 60)
    
    # SEC company tickers
    sec_tickers_path = DATA_DIR / "sec_company_tickers.json"
    if sec_tickers_path.exists():
        print("\nSEC Company Tickers:")
        with open(sec_tickers_path, 'r') as f:
            data = json.load(f)
        
        # The format is {index: {cik_str, ticker, title}}
        print(f"  Total entries: {len(data):,}")
        
        # Sample
        for key in list(data.keys())[:3]:
            entry = data[key]
            print(f"    {entry}")
    
    # SEC with exchange
    sec_exchange_path = DATA_DIR / "sec_company_tickers_exchange.json"
    if sec_exchange_path.exists():
        print("\nSEC Company Tickers with Exchange:")
        with open(sec_exchange_path, 'r') as f:
            data = json.load(f)
        
        if 'data' in data:
            entries = data['data']
            print(f"  Total entries: {len(entries):,}")
            
            # Check fields
            if len(entries) > 0:
                print(f"  Fields: {list(entries[0].keys()) if isinstance(entries[0], dict) else entries[0]}")
                print(f"  Sample: {entries[:2]}")
    
    # GLEIF BIC-LEI
    gleif_dir = DATA_DIR.parent / "gleif"
    for f in gleif_dir.glob("bic-lei*.csv"):
        print(f"\nGLEIF BIC-LEI: {f.name}")
        import csv
        with open(f, 'r') as fh:
            reader = csv.DictReader(fh)
            rows = list(reader)
            print(f"  Total entries: {len(rows):,}")
            if rows:
                print(f"  Fields: {list(rows[0].keys())}")
                print(f"  Sample: {rows[0]}")
    
    # GLEIF ISIN-LEI (already downloaded)
    isin_lei_path = gleif_dir / "lei-isin-20260129T081545.csv"
    if isin_lei_path.exists():
        print(f"\nGLEIF ISIN-LEI: {isin_lei_path.name}")
        with open(isin_lei_path, 'r') as f:
            lines = sum(1 for _ in f)
        print(f"  Total entries: {lines:,}")


def main():
    print("=" * 60)
    print("Bulk Reference Data Downloader")
    print("=" * 60)
    print(f"Output directory: {DATA_DIR}")
    
    # Download SEC data
    download_sec_data()
    
    # Download GLEIF BIC-LEI
    download_gleif_bic_lei()
    
    # Get GLEIF LEI index (don't download full file - it's huge)
    download_gleif_lei_index()
    
    # Analyze what we have
    analyze_downloaded_data()
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("""
Available for entity mapping:
1. SEC CIK -> Ticker, Name, Exchange (fresh, authoritative for US public companies)
2. GLEIF ISIN -> LEI (7.8M mappings, fresh)
3. GLEIF BIC -> LEI (bank identifiers)
4. Your data (Thomson, Bloomberg, FactSet) - older but comprehensive

Recommended approach:
- Use SEC data as ground truth for US public companies (fresh, authoritative)
- Use GLEIF ISIN-LEI to link Thomson (LEI) <-> other sources (ISIN)
- Use your FactSet/Bloomberg data for historical cross-referencing
- Flag any conflicts for manual review
""")


if __name__ == "__main__":
    main()
