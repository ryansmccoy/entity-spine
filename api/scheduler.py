"""
EntitySpine Data Refresh Scheduler

Background tasks for keeping reference data fresh.

The SEC updates company_tickers.json daily. GLEIF updates LEI data weekly.

Usage:
    # Run as standalone cron job
    python -m api.scheduler refresh-sec
    python -m api.scheduler refresh-all
    
    # Or use the API's built-in scheduler (enabled by default)
    # Set ENTITYSPINE_AUTO_REFRESH=false to disable
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from entityspine.stores.sqlite_store import SqliteStore


class RefreshScheduler:
    """
    Background scheduler for refreshing EntitySpine data.
    
    Refresh intervals:
    - SEC company_tickers.json: Daily (changes frequently)
    - GLEIF LEI-ISIN: Weekly (large file, changes slowly)
    - GLEIF LEI-BIC: Weekly
    """
    
    def __init__(
        self,
        db_path: Optional[str] = None,
        sec_interval_hours: int = 24,
        gleif_interval_hours: int = 168,  # 7 days
    ):
        self.db_path = db_path or os.environ.get(
            "ENTITYSPINE_DB_PATH",
            str(Path.home() / ".entityspine" / "entityspine.db")
        )
        self.sec_interval = timedelta(hours=sec_interval_hours)
        self.gleif_interval = timedelta(hours=gleif_interval_hours)
        self._running = False
        self._last_sec_refresh: Optional[datetime] = None
        self._last_gleif_refresh: Optional[datetime] = None
        self._metadata_file = Path(self.db_path).parent / "refresh_metadata.json"
        self._load_metadata()
    
    def _load_metadata(self):
        """Load last refresh times from metadata file."""
        if self._metadata_file.exists():
            try:
                with open(self._metadata_file) as f:
                    data = json.load(f)
                if data.get("last_sec_refresh"):
                    self._last_sec_refresh = datetime.fromisoformat(data["last_sec_refresh"])
                if data.get("last_gleif_refresh"):
                    self._last_gleif_refresh = datetime.fromisoformat(data["last_gleif_refresh"])
                logger.info(f"Loaded refresh metadata: SEC={self._last_sec_refresh}, GLEIF={self._last_gleif_refresh}")
            except Exception as e:
                logger.warning(f"Could not load refresh metadata: {e}")
    
    def _save_metadata(self):
        """Save last refresh times to metadata file."""
        try:
            data = {
                "last_sec_refresh": self._last_sec_refresh.isoformat() if self._last_sec_refresh else None,
                "last_gleif_refresh": self._last_gleif_refresh.isoformat() if self._last_gleif_refresh else None,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            with open(self._metadata_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save refresh metadata: {e}")
    
    def refresh_sec_data(self) -> int:
        """
        Refresh SEC company tickers from SEC website.
        
        Downloads fresh company_tickers.json and updates the database.
        
        Returns:
            Number of entities updated/added.
        """
        logger.info("Refreshing SEC company tickers...")
        
        try:
            store = SqliteStore(self.db_path)
            store.initialize()
            
            count = store.load_sec_data()
            
            self._last_sec_refresh = datetime.now(timezone.utc)
            self._save_metadata()
            
            logger.info(f"SEC refresh complete: {count:,} entities")
            return count
            
        except Exception as e:
            logger.error(f"SEC refresh failed: {e}")
            raise
    
    def refresh_gleif_data(self) -> dict:
        """
        Refresh GLEIF LEI-ISIN and LEI-BIC mappings.
        
        Note: This downloads large files (~300MB). Only run periodically.
        
        Returns:
            Dict with counts for each data type.
        """
        logger.info("Refreshing GLEIF data (this may take several minutes)...")
        
        # TODO: Implement GLEIF download from their API
        # For now, just update metadata
        # https://www.gleif.org/en/lei-data/gleif-concatenated-file/download-the-concatenated-file
        
        self._last_gleif_refresh = datetime.now(timezone.utc)
        self._save_metadata()
        
        logger.info("GLEIF refresh: Using cached data (download not yet implemented)")
        return {"lei_isin": 0, "lei_bic": 0, "status": "cached"}
    
    def needs_sec_refresh(self) -> bool:
        """Check if SEC data needs refresh."""
        if not self._last_sec_refresh:
            return True
        return datetime.now(timezone.utc) - self._last_sec_refresh > self.sec_interval
    
    def needs_gleif_refresh(self) -> bool:
        """Check if GLEIF data needs refresh."""
        if not self._last_gleif_refresh:
            return True
        return datetime.now(timezone.utc) - self._last_gleif_refresh > self.gleif_interval
    
    def get_status(self) -> dict:
        """Get scheduler status."""
        now = datetime.now(timezone.utc)
        return {
            "running": self._running,
            "database": self.db_path,
            "sec": {
                "last_refresh": self._last_sec_refresh.isoformat() if self._last_sec_refresh else None,
                "interval_hours": self.sec_interval.total_seconds() / 3600,
                "needs_refresh": self.needs_sec_refresh(),
                "next_refresh": (self._last_sec_refresh + self.sec_interval).isoformat() if self._last_sec_refresh else "now",
            },
            "gleif": {
                "last_refresh": self._last_gleif_refresh.isoformat() if self._last_gleif_refresh else None,
                "interval_hours": self.gleif_interval.total_seconds() / 3600,
                "needs_refresh": self.needs_gleif_refresh(),
                "next_refresh": (self._last_gleif_refresh + self.gleif_interval).isoformat() if self._last_gleif_refresh else "now",
            },
        }
    
    async def run_async(self):
        """
        Run scheduler as async background task.
        
        Checks for needed refreshes every hour.
        """
        self._running = True
        logger.info("EntitySpine refresh scheduler started")
        
        while self._running:
            try:
                if self.needs_sec_refresh():
                    logger.info("SEC data is stale, refreshing...")
                    await asyncio.get_event_loop().run_in_executor(
                        None, self.refresh_sec_data
                    )
                
                # GLEIF refresh disabled until download is implemented
                # if self.needs_gleif_refresh():
                #     await asyncio.get_event_loop().run_in_executor(
                #         None, self.refresh_gleif_data
                #     )
                
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
            
            # Check every hour
            await asyncio.sleep(3600)
    
    def stop(self):
        """Stop the scheduler."""
        self._running = False
        logger.info("EntitySpine refresh scheduler stopped")


# Global scheduler instance
_scheduler: Optional[RefreshScheduler] = None


def get_scheduler() -> RefreshScheduler:
    """Get or create the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = RefreshScheduler()
    return _scheduler


async def start_background_refresh():
    """Start background refresh task (called from FastAPI startup)."""
    if os.environ.get("ENTITYSPINE_AUTO_REFRESH", "true").lower() == "false":
        logger.info("Auto-refresh disabled by ENTITYSPINE_AUTO_REFRESH=false")
        return
    
    scheduler = get_scheduler()
    asyncio.create_task(scheduler.run_async())


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    """CLI entry point."""
    import argparse
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    
    parser = argparse.ArgumentParser(description="EntitySpine Data Refresh")
    parser.add_argument(
        "command",
        choices=["refresh-sec", "refresh-gleif", "refresh-all", "status"],
        help="Command to run"
    )
    parser.add_argument(
        "--db-path",
        help="Path to EntitySpine database",
        default=None
    )
    
    args = parser.parse_args()
    
    scheduler = RefreshScheduler(db_path=args.db_path)
    
    if args.command == "status":
        import json
        print(json.dumps(scheduler.get_status(), indent=2))
    
    elif args.command == "refresh-sec":
        count = scheduler.refresh_sec_data()
        print(f"Refreshed {count:,} SEC entities")
    
    elif args.command == "refresh-gleif":
        result = scheduler.refresh_gleif_data()
        print(f"GLEIF refresh: {result}")
    
    elif args.command == "refresh-all":
        sec_count = scheduler.refresh_sec_data()
        gleif_result = scheduler.refresh_gleif_data()
        print(f"SEC: {sec_count:,} entities")
        print(f"GLEIF: {gleif_result}")


if __name__ == "__main__":
    main()
