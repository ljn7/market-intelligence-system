import os
import pandas as pd
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def save_tweets_parquet(tweets: List[Dict], output_dir="data/parquet", filename_prefix="nitter"):
    ensure_dir(output_dir)
    if not tweets:
        logger.info("No tweets to save")
        return None
    df = pd.DataFrame(tweets)
    # normalize columns and types
    if "timestamp" in df.columns:
        df["scraped_at"] = pd.to_datetime(df.get("scraped_at", pd.Timestamp.utcnow()))
    # dedupe
    df.drop_duplicates(subset=["tweet_id"], inplace=True)
    ts = pd.Timestamp.utcnow().strftime("%Y%m%dT%H%M%SZ")
    path = os.path.join(output_dir, f"{filename_prefix}_{ts}.parquet")
    df.to_parquet(path, index=False)
    # also save a "latest" snapshot
    latest = os.path.join(output_dir, f"{filename_prefix}_latest.parquet")
    df.to_parquet(latest, index=False)
    logger.info("Saved %d tweets to %s", len(df), path)
    return path
