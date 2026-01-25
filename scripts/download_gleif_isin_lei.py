"""Download GLEIF ISIN-to-LEI relationship files."""
import os
import json
import zipfile
import urllib.request
from pathlib import Path

GLEIF_DIR = Path(__file__).parent.parent / "entityspine_data" / "gleif"
GLEIF_DIR.mkdir(parents=True, exist_ok=True)

def get_latest_file_info():
    """Get info about the latest ISIN-LEI mapping file."""
    url = 'https://mapping.gleif.org/api/v2/isin-lei/'
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept': 'application/vnd.api+json'
        }
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    
    # Get the most recent file (first in the list)
    latest = data['data'][0]
    file_id = latest['id']
    filename = latest['attributes']['fileName']
    uploaded_at = latest['attributes']['uploadedAt']
    
    print(f"Latest ISIN-LEI file:")
    print(f"  ID: {file_id}")
    print(f"  Filename: {filename}")
    print(f"  Uploaded: {uploaded_at}")
    
    return file_id, filename


def download_file(file_id: str, filename: str):
    """Download the ISIN-LEI mapping file."""
    # The download endpoint
    download_url = f'https://mapping.gleif.org/api/v2/isin-lei/{file_id}/download'
    
    output_path = GLEIF_DIR / filename
    
    if output_path.exists():
        print(f"File already exists: {output_path}")
        return output_path
    
    print(f"Downloading from: {download_url}")
    
    req = urllib.request.Request(
        download_url,
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        }
    )
    
    with urllib.request.urlopen(req, timeout=300) as resp:
        content_length = resp.headers.get('Content-Length')
        if content_length:
            print(f"File size: {int(content_length) / 1024 / 1024:.1f} MB")
        
        with open(output_path, 'wb') as f:
            total = 0
            while True:
                chunk = resp.read(8192 * 16)  # 128KB chunks
                if not chunk:
                    break
                f.write(chunk)
                total += len(chunk)
                if total % (1024 * 1024 * 10) < len(chunk):  # Every 10MB
                    print(f"  Downloaded: {total / 1024 / 1024:.1f} MB")
    
    print(f"Saved to: {output_path}")
    return output_path


def extract_and_preview(zip_path: Path):
    """Extract the zip and preview the contents."""
    print(f"\nExtracting {zip_path}...")
    
    extract_dir = zip_path.parent
    
    with zipfile.ZipFile(zip_path, 'r') as zf:
        names = zf.namelist()
        print(f"Contents: {names}")
        
        for name in names:
            zf.extract(name, extract_dir)
            extracted_path = extract_dir / name
            print(f"\nExtracted: {extracted_path}")
            
            # Preview first few lines
            with open(extracted_path, 'r', encoding='utf-8') as f:
                print("\nFirst 10 lines:")
                for i, line in enumerate(f):
                    if i >= 10:
                        break
                    print(f"  {line.rstrip()[:100]}")
            
            # Count lines
            with open(extracted_path, 'r', encoding='utf-8') as f:
                line_count = sum(1 for _ in f)
            print(f"\nTotal lines: {line_count:,}")
            
            return extracted_path
    
    return None


def main():
    print("=" * 60)
    print("GLEIF ISIN-to-LEI Mapping Download")
    print("=" * 60)
    
    # Get latest file info
    file_id, filename = get_latest_file_info()
    
    # Download the file
    zip_path = download_file(file_id, filename)
    
    # Extract and preview
    csv_path = extract_and_preview(zip_path)
    
    if csv_path:
        print(f"\n✓ Ready for processing: {csv_path}")


if __name__ == "__main__":
    main()
