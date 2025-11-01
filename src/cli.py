import argparse
import logging
from .logger_config import setup_logging
from .config import load_config
from .scraper import NitterSeleniumScraper
from .storage import save_tweets_parquet
from .processor import prepare_corpus, compute_tfidf_features, aggregate_signal_from_tfidf
from .analyzer import build_composite_signal
import os
import json

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", "-c", required=True, help="Path to config.yaml")
    args = parser.parse_args()
    cfg = load_config(args.config)
    setup_logging(cfg.get("log_file", "logs/twitter_scraper.log"))
    logger = logging.getLogger(__name__)
    os.makedirs(cfg.get("output_dir","data/parquet"), exist_ok=True)

    scraper = NitterSeleniumScraper(cfg)
    try:
        tweets = scraper.scrape_hashtags(cfg.get("hashtags", []), cfg.get("target_count", 2000))
        path = save_tweets_parquet(tweets, output_dir=cfg.get("output_dir","data/parquet"))
        # processing
        texts = prepare_corpus(tweets)
        vect, X = compute_tfidf_features(texts,
                                        max_features=cfg.get("tfidf_max_features",10000),
                                        ngram_range=tuple(cfg.get("tfidf_ngram_range",[1,2])))
        features = aggregate_signal_from_tfidf(X, vect, top_k=30)
        signals = build_composite_signal(tweets, vect, X, top_k=40)
        # dump a summary JSON
        summary = {
            "saved_path": path,
            "num_tweets": len(tweets),
            "top_terms": features,
            "top_signals": signals["top_signals"]
        }
        summary_path = os.path.join(cfg.get("output_dir","data/parquet"), "summary.json")
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)
        logger.info("Summary saved to %s", summary_path)
    finally:
        scraper.close()

if __name__ == "__main__":
    main()
