"""Analyze Compustat CIK mapping file."""
import pandas as pd

df = pd.read_excel('G:/COMPUSTAT/2c2c0744baa30992_cik_gvkey_cusip_ticker_filings.xlsx')
print(f'Total rows: {len(df):,}')
print(f'Unique CIKs: {df["cik"].nunique():,}')
print(f'Unique GVKEYs: {df["gvkey"].nunique():,}')
print(f'Unique CUSIPs: {df["CUSIPH"].nunique():,}')
print(f'Unique Tickers: {df["TICKERH"].nunique():,}')

# Check NVIDIA
nvidia = df[df['coname'].str.contains('NVIDIA', case=False, na=False)]
print('\nNVIDIA:')
print(nvidia[['cik', 'coname', 'gvkey', 'CUSIPH', 'TICKERH']])
