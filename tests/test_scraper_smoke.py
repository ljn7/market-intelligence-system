# This is a smoke test that will only run if a display/chrome is available.
# It's intended as a sanity check, not for CI.
import pytest
from src.scraper import NitterSeleniumScraper
from src.config import load_config

@pytest.mark.skip(reason="Requires Chrome/undetected-chromedriver and network")
def test_scraper_smoke():
    cfg = load_config("config.yaml")
    s = NitterSeleniumScraper(cfg)
    try:
        tweets = s.scrape_hashtags(cfg.get("hashtags", [])[:1], target_count=5)
        assert isinstance(tweets, list)
    finally:
        s.close()
