"""
Download additional bulk reference data with proper headers.
"""
import os
import json
import gzip
import zipfile
import urllib.request
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "entityspine_data" / "bulk_reference"
DATA_DIR.mkdir(parents=True, exist_ok=True)
GLEIF_DIR = Path(__file__).parent.parent / "entityspine_data" / "gleif"


def download_sec_data():
    """Download SEC EDGAR reference files with proper headers."""
    print("=" * 60)
    print("SEC EDGAR Data")
    print("=" * 60)
    
    # SEC requires a proper User-Agent with contact info
    headers = {
        'User-Agent': 'EntitySpine/1.0 (contact@example.com)',
        'Accept': 'application/json',
        'Accept-Encoding': 'gzip, deflate',
    }
    
    files = [
        ("https://www.sec.gov/files/company_tickers.json", "sec_company_tickers.json"),
        ("https://www.sec.gov/files/company_tickers_exchange.json", "sec_company_tickers_exchange.json"),
    ]
    
    for url, filename in files:
        output_path = DATA_DIR / filename
        print(f"\nDownloading: {filename}")
        
        if output_path.exists():
            print(f"  Already exists: {output_path}")
            continue
        
        req = urllib.request.Request(url, headers=headers)
        
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = resp.read()
                
                # Handle gzip
                if resp.headers.get('Content-Encoding') == 'gzip':
                    import io
                    data = gzip.decompress(data)
                
                with open(output_path, 'wb') as f:
                    f.write(data)
                
                print(f"  Saved: {output_path}")
                
                # Parse and show stats
                json_data = json.loads(data)
                if isinstance(json_data, dict):
                    if 'data' in json_data:
                        print(f"  Entries: {len(json_data['data']):,}")
                    else:
                        print(f"  Entries: {len(json_data):,}")
                        
        except Exception as e:
            print(f"  ERROR: {e}")


def download_gleif_full_lei():
    """Download the full GLEIF LEI golden copy (Level 1 data)."""
    print("\n" + "=" * 60)
    print("GLEIF Full LEI Data (Golden Copy)")
    print("=" * 60)
    
    # Read the index we saved earlier
    index_path = DATA_DIR / "gleif_lei_index.json"
    if not index_path.exists():
        print("  No index file found. Run download_bulk_reference.py first.")
        return
    
    with open(index_path, 'r') as f:
        index = json.load(f)
    
    # Get the latest full file URL
    if 'data' in index and len(index['data']) > 0:
        latest = index['data'][0]
        
        # Get CSV URL
        csv_url = None
        if 'lei2' in latest and 'full_file' in latest['lei2']:
            csv_info = latest['lei2']['full_file'].get('csv', {})
            csv_url = csv_info.get('url')
            record_count = csv_info.get('record_count', 0)
            size_human = csv_info.get('size_human_readable', 'unknown')
        
        if csv_url:
            print(f"  URL: {csv_url[:80]}...")
            print(f"  Records: {record_count:,}")
            print(f"  Size: {size_human}")
            
            # Download
            output_path = GLEIF_DIR / "gleif_lei_full.csv.zip"
            
            if output_path.exists():
                print(f"  Already exists: {output_path}")
            else:
                print(f"  Downloading (this may take a few minutes)...")
                
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                req = urllib.request.Request(csv_url, headers=headers)
                
                try:
                    with urllib.request.urlopen(req, timeout=600) as resp:
                        total = 0
                        with open(output_path, 'wb') as f:
                            while True:
                                chunk = resp.read(8192 * 128)  # 1MB chunks
                                if not chunk:
                                    break
                                f.write(chunk)
                                total += len(chunk)
                                if total % (50 * 1024 * 1024) < len(chunk):
                                    print(f"    Downloaded: {total / 1024 / 1024:.0f} MB")
                        
                        print(f"  Saved: {output_path}")
                except Exception as e:
                    print(f"  ERROR: {e}")
                    if output_path.exists():
                        output_path.unlink()
                    return
            
            # Extract
            csv_output = GLEIF_DIR / "gleif_lei_full.csv"
            if not csv_output.exists() and output_path.exists():
                print("  Extracting...")
                try:
                    with zipfile.ZipFile(output_path, 'r') as zf:
                        # Find the CSV file
                        for name in zf.namelist():
                            if name.endswith('.csv'):
                                print(f"    Extracting: {name}")
                                zf.extract(name, GLEIF_DIR)
                                # Rename to standard name
                                extracted = GLEIF_DIR / name
                                if extracted != csv_output:
                                    extracted.rename(csv_output)
                                break
                except Exception as e:
                    print(f"  Extract ERROR: {e}")
            
            # Preview
            if csv_output.exists():
                print(f"\n  Preview of {csv_output.name}:")
                with open(csv_output, 'r', encoding='utf-8') as f:
                    for i, line in enumerate(f):
                        if i == 0:
                            # Header
                            cols = line.strip().split(',')
                            print(f"    Columns ({len(cols)}): {cols[:10]}...")
                        elif i <= 3:
                            print(f"    Row {i}: {line[:100].strip()}...")
                        else:
                            break


def analyze_sec_data():
    """Analyze SEC data for mapping potential."""
    print("\n" + "=" * 60)
    print("SEC Data Analysis")
    print("=" * 60)
    
    # Basic tickers
    path = DATA_DIR / "sec_company_tickers.json"
    if path.exists():
        with open(path, 'r') as f:
            data = json.load(f)
        
        print(f"\nSEC Company Tickers:")
        print(f"  Total entries: {len(data):,}")
        
        # Sample
        for key in list(data.keys())[:3]:
            entry = data[key]
            print(f"    {entry}")
        
        # Check for NVIDIA
        for key, entry in data.items():
            if 'NVIDIA' in entry.get('title', '').upper() or entry.get('ticker') == 'NVDA':
                print(f"\n  NVIDIA found:")
                print(f"    {entry}")
                break
    
    # With exchange
    path = DATA_DIR / "sec_company_tickers_exchange.json"
    if path.exists():
        with open(path, 'r') as f:
            data = json.load(f)
        
        entries = data.get('data', [])
        print(f"\nSEC Company Tickers with Exchange:")
        print(f"  Total entries: {len(entries):,}")
        
        if entries:
            # Check structure
            print(f"  Fields: {data.get('fields', 'N/A')}")
            print(f"  Sample (first 2):")
            for entry in entries[:2]:
                print(f"    {entry}")
            
            # Check for NVIDIA
            for entry in entries:
                if len(entry) >= 2:
                    if 'NVIDIA' in str(entry[1]).upper() or entry[2] == 'NVDA' if len(entry) > 2 else False:
                        print(f"\n  NVIDIA found:")
                        print(f"    {entry}")
                        break


def main():
    # Download SEC data
    download_sec_data()
    
    # Analyze SEC data
    analyze_sec_data()
    
    # Download GLEIF full LEI
    download_gleif_full_lei()
    
    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)


if __name__ == "__main__":
    main()
