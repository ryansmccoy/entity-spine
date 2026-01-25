#!/usr/bin/env python3
"""
Multi-Source Data Ingestion Pipeline

Converts FactSet, Bloomberg, and Thomson data to Parquet and loads into EntitySpine.

Usage:
    python -m entityspine.data.ingest --factset "G:/FACTSET/public_private/ff_pubpriv_companies_all.csv"
    python -m entityspine.data.ingest --bloomberg "G:/BLOOMBERG"
    python -m entityspine.data.ingest --thomson "G:/THOMSON"
    python -m entityspine.data.ingest --all  # Load all configured sources
"""

import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from entityspine.data.source_metadata import (
    SourceMetadata, DataSourceType, extract_vendor_date, detect_source_type
)
from entityspine.data.parquet_store import ParquetEntityStore
from entityspine.data.loaders import (
    iter_factset_csv, load_factset_batch,
    iter_bloomberg_bbuid, load_bloomberg_batch,
    iter_thomson_ttl, load_thomson_batch,
)


def format_size(size_bytes: int) -> str:
    """Format bytes as human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if abs(size_bytes) < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def format_rate(count: int, seconds: float) -> str:
    """Format rate as items per second."""
    rate = count / seconds if seconds > 0 else 0
    return f"{rate:,.0f}/sec"


def count_file_lines(file_path: Path) -> int:
    """Count lines in a file (for progress estimation)."""
    with open(file_path, 'rb') as f:
        return sum(1 for _ in f)


def ingest_factset(
    file_path: str,
    store: ParquetEntityStore,
    batch_size: int = 10000,
    max_rows: Optional[int] = None,
) -> dict:
    """
    Ingest FactSet data into the store.
    
    Returns stats dict.
    """
    path = Path(file_path)
    print(f"\n{'='*60}")
    print(f"FACTSET INGESTION")
    print(f"{'='*60}")
    print(f"Source: {path.name}")
    print(f"Size:   {format_size(path.stat().st_size)}")
    
    start_time = time.time()
    total_entities = 0
    total_securities = 0
    total_listings = 0
    total_claims = 0
    total_rows = 0
    
    # Process batches
    for batch_idx, batch in enumerate(iter_factset_csv(path, batch_size)):
        if max_rows and total_rows >= max_rows:
            break
            
        # Limit batch if max_rows
        if max_rows and total_rows + len(batch) > max_rows:
            batch = batch[:max_rows - total_rows]
        
        entities, securities, listings, claims = load_factset_batch(batch)
        
        store.save_entities(
            entities=entities,
            securities=securities,
            listings=listings,
            claims=claims,
            append=True,
        )
        
        total_entities += len(entities)
        total_securities += len(securities)
        total_listings += len(listings)
        total_claims += len(claims)
        total_rows += len(batch)
        
        elapsed = time.time() - start_time
        print(f"  Batch {batch_idx + 1}: {total_rows:,} rows | "
              f"{total_entities:,} entities | "
              f"{format_rate(total_rows, elapsed)}", end='\r')
    
    elapsed = time.time() - start_time
    
    # Create metadata (skip hash for large files)
    metadata = SourceMetadata.from_file(
        path,
        DataSourceType.FACTSET,
        row_count=total_rows,
        vendor_date=extract_vendor_date(path.name),
        compute_hash=path.stat().st_size < 100_000_000,  # Only hash files < 100MB
    )
    store.add_source(metadata)
    
    print(f"\n\nFactSet Complete:")
    print(f"  Rows processed:  {total_rows:,}")
    print(f"  Entities:        {total_entities:,}")
    print(f"  Securities:      {total_securities:,}")
    print(f"  Listings:        {total_listings:,}")
    print(f"  Identifiers:     {total_claims:,}")
    print(f"  Time:            {elapsed:.1f}s ({format_rate(total_rows, elapsed)})")
    
    return {
        'source': 'factset',
        'rows': total_rows,
        'entities': total_entities,
        'securities': total_securities,
        'listings': total_listings,
        'claims': total_claims,
        'time_seconds': elapsed,
    }


def ingest_bloomberg(
    directory: str,
    store: ParquetEntityStore,
    batch_size: int = 10000,
    max_rows: Optional[int] = None,
    file_patterns: Optional[List[str]] = None,
) -> dict:
    """
    Ingest Bloomberg BBUID data from directory.
    
    Processes all .txt files matching patterns (default: Equity_*).
    
    Returns stats dict.
    """
    dir_path = Path(directory)
    print(f"\n{'='*60}")
    print(f"BLOOMBERG INGESTION")
    print(f"{'='*60}")
    print(f"Directory: {dir_path}")
    
    # Find files to process
    if file_patterns is None:
        file_patterns = ['Equity_Common_Stock_*.txt', 'Equity_*.txt']
    
    files_to_process = []
    
    # Check for folder structure (Bloomberg splits large files into folders)
    for pattern in file_patterns:
        # Direct files
        files_to_process.extend(dir_path.glob(pattern))
        # Files in subfolders (e.g., Equity_Common_Stock_20160530.txt/Equity_Common_Stock_01_20160530.txt)
        for subfolder in dir_path.iterdir():
            if subfolder.is_dir() and any(subfolder.name.startswith(p.replace('*.txt', '').replace('*', '')) 
                                          for p in file_patterns):
                files_to_process.extend(subfolder.glob('*.txt'))
    
    files_to_process = sorted(set(files_to_process))
    print(f"Found {len(files_to_process)} files to process")
    
    if not files_to_process:
        print("No matching files found!")
        return {'source': 'bloomberg', 'rows': 0}
    
    start_time = time.time()
    total_entities = 0
    total_securities = 0
    total_listings = 0
    total_claims = 0
    total_rows = 0
    
    for file_idx, file_path in enumerate(files_to_process):
        if max_rows and total_rows >= max_rows:
            break
            
        print(f"\n  [{file_idx + 1}/{len(files_to_process)}] {file_path.name}")
        file_rows = 0
        
        for batch_idx, batch in enumerate(iter_bloomberg_bbuid(file_path, batch_size)):
            if max_rows and total_rows >= max_rows:
                break
                
            if max_rows and total_rows + len(batch) > max_rows:
                batch = batch[:max_rows - total_rows]
            
            entities, securities, listings, claims = load_bloomberg_batch(batch)
            
            store.save_entities(
                entities=entities,
                securities=securities,
                listings=listings,
                claims=claims,
                append=True,
            )
            
            total_entities += len(entities)
            total_securities += len(securities)
            total_listings += len(listings)
            total_claims += len(claims)
            total_rows += len(batch)
            file_rows += len(batch)
            
            elapsed = time.time() - start_time
            print(f"    Batch {batch_idx + 1}: {file_rows:,} rows | "
                  f"{total_rows:,} total | "
                  f"{format_rate(total_rows, elapsed)}", end='\r')
        
        # Create metadata for this file
        metadata = SourceMetadata.from_file(
            file_path,
            DataSourceType.BLOOMBERG,
            row_count=file_rows,
            vendor_date=extract_vendor_date(file_path.name),
            compute_hash=file_path.stat().st_size < 50_000_000,
        )
        store.add_source(metadata)
        print()  # newline after file
    
    elapsed = time.time() - start_time
    
    print(f"\nBloomberg Complete:")
    print(f"  Files processed: {len(files_to_process)}")
    print(f"  Rows processed:  {total_rows:,}")
    print(f"  Entities:        {total_entities:,}")
    print(f"  Securities:      {total_securities:,}")
    print(f"  Listings:        {total_listings:,}")
    print(f"  Identifiers:     {total_claims:,}")
    print(f"  Time:            {elapsed:.1f}s ({format_rate(total_rows, elapsed)})")
    
    return {
        'source': 'bloomberg',
        'files': len(files_to_process),
        'rows': total_rows,
        'entities': total_entities,
        'securities': total_securities,
        'listings': total_listings,
        'claims': total_claims,
        'time_seconds': elapsed,
    }


def ingest_thomson(
    directory: str,
    store: ParquetEntityStore,
    batch_size: int = 5000,
    max_rows: Optional[int] = None,
) -> dict:
    """
    Ingest Thomson OpenPermID data from directory.
    
    Processes organization TTL files (gzipped).
    
    Returns stats dict.
    """
    dir_path = Path(directory)
    print(f"\n{'='*60}")
    print(f"THOMSON OPENPERMID INGESTION")
    print(f"{'='*60}")
    print(f"Directory: {dir_path}")
    
    # Find organization files (the main entity data)
    files_to_process = list(dir_path.glob('OpenPermID-bulk-organization-*.ttl.gz'))
    files_to_process = sorted(files_to_process)
    
    print(f"Found {len(files_to_process)} organization files")
    
    if not files_to_process:
        print("No organization files found!")
        return {'source': 'thomson', 'rows': 0}
    
    # Use the most recent file
    file_path = files_to_process[-1]
    print(f"Using: {file_path.name} ({format_size(file_path.stat().st_size)} compressed)")
    
    start_time = time.time()
    total_entities = 0
    total_claims = 0
    total_rows = 0
    
    for batch_idx, batch in enumerate(iter_thomson_ttl(file_path, batch_size)):
        if max_rows and total_rows >= max_rows:
            break
            
        if max_rows and total_rows + len(batch) > max_rows:
            batch = batch[:max_rows - total_rows]
        
        entities, _, _, claims = load_thomson_batch(batch)
        
        store.save_entities(
            entities=entities,
            claims=claims,
            append=True,
        )
        
        total_entities += len(entities)
        total_claims += len(claims)
        total_rows += len(batch)
        
        elapsed = time.time() - start_time
        print(f"  Batch {batch_idx + 1}: {total_rows:,} entities | "
              f"{format_rate(total_rows, elapsed)}", end='\r')
    
    elapsed = time.time() - start_time
    
    # Create metadata
    metadata = SourceMetadata.from_file(
        file_path,
        DataSourceType.THOMSON_PERMID,
        row_count=total_rows,
        vendor_date=extract_vendor_date(file_path.name),
        compute_hash=False,  # Large gzipped files
    )
    store.add_source(metadata)
    
    print(f"\n\nThomson Complete:")
    print(f"  Rows processed:  {total_rows:,}")
    print(f"  Entities:        {total_entities:,}")
    print(f"  Identifiers:     {total_claims:,}")
    print(f"  Time:            {elapsed:.1f}s ({format_rate(total_rows, elapsed)})")
    
    return {
        'source': 'thomson',
        'rows': total_rows,
        'entities': total_entities,
        'claims': total_claims,
        'time_seconds': elapsed,
    }


def main():
    parser = argparse.ArgumentParser(
        description='Multi-source entity data ingestion',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=r"""
Examples:
  # Load FactSet data
  python -m entityspine.data.ingest --factset "G:\FACTSET\public_private\ff_pubpriv_companies_all.csv"
  
  # Load Bloomberg BBUID data
  python -m entityspine.data.ingest --bloomberg "G:\BLOOMBERG"
  
  # Load Thomson OpenPermID data
  python -m entityspine.data.ingest --thomson "G:\THOMSON"
  
  # Load all with row limit for testing
  python -m entityspine.data.ingest --factset path --bloomberg path --thomson path --max-rows 50000
        """,
    )
    
    parser.add_argument('--factset', type=str, help='Path to FactSet CSV file')
    parser.add_argument('--bloomberg', type=str, help='Path to Bloomberg directory')
    parser.add_argument('--thomson', type=str, help='Path to Thomson directory')
    parser.add_argument('--output', type=str, default='./entityspine_data',
                        help='Output directory for Parquet files (default: ./entityspine_data)')
    parser.add_argument('--batch-size', type=int, default=10000,
                        help='Batch size for processing (default: 10000)')
    parser.add_argument('--max-rows', type=int, help='Maximum rows to process per source')
    parser.add_argument('--stats', action='store_true', help='Show store statistics')
    
    args = parser.parse_args()
    
    # Initialize store
    store = ParquetEntityStore(args.output)
    
    if args.stats:
        stats = store.get_stats()
        print("\nEntity Store Statistics:")
        print(f"  Entities:   {stats['entities']:,}")
        print(f"  Securities: {stats['securities']:,}")
        print(f"  Listings:   {stats['listings']:,}")
        print(f"  Sources:    {stats['sources']}")
        print(f"\nParquet Files:")
        for name, info in stats['files'].items():
            if info.get('exists'):
                print(f"  {name}.parquet: {info['size_mb']} MB")
            else:
                print(f"  {name}.parquet: (not created)")
        return
    
    all_stats = []
    
    # Run ingestions
    if args.factset:
        stats = ingest_factset(args.factset, store, args.batch_size, args.max_rows)
        all_stats.append(stats)
    
    if args.bloomberg:
        stats = ingest_bloomberg(args.bloomberg, store, args.batch_size, args.max_rows)
        all_stats.append(stats)
    
    if args.thomson:
        stats = ingest_thomson(args.thomson, store, args.batch_size, args.max_rows)
        all_stats.append(stats)
    
    if not any([args.factset, args.bloomberg, args.thomson]):
        parser.print_help()
        return
    
    # Summary
    print(f"\n{'='*60}")
    print("INGESTION SUMMARY")
    print(f"{'='*60}")
    
    total_entities = sum(s.get('entities', 0) for s in all_stats)
    total_securities = sum(s.get('securities', 0) for s in all_stats)
    total_listings = sum(s.get('listings', 0) for s in all_stats)
    total_time = sum(s.get('time_seconds', 0) for s in all_stats)
    
    for stats in all_stats:
        print(f"\n{stats['source'].upper()}:")
        print(f"  Rows:       {stats.get('rows', 0):,}")
        print(f"  Entities:   {stats.get('entities', 0):,}")
    
    print(f"\nTOTALS:")
    print(f"  Entities:   {total_entities:,}")
    print(f"  Securities: {total_securities:,}")
    print(f"  Listings:   {total_listings:,}")
    print(f"  Time:       {total_time:.1f}s")
    
    # Show final store stats
    final_stats = store.get_stats()
    print(f"\nFinal Store State:")
    print(f"  Output:     {args.output}")
    for name, info in final_stats['files'].items():
        if info.get('exists'):
            print(f"  {name}.parquet: {info['size_mb']} MB")


if __name__ == '__main__':
    main()
