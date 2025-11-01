import logging
import random
import time
import socket
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import List, Optional, Set, Dict
from urllib.parse import quote
from bs4 import BeautifulSoup
import re
import os

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc

from .utils import clean_text, parse_hashtags, parse_mentions, backoff_sleep

logger = logging.getLogger(__name__)

@dataclass
class Tweet:
    tweet_id: str
    username: str
    display_name: str
    timestamp: str
    content: str
    likes: int
    retweets: int
    replies: int
    views: int
    hashtags: List[str]
    mentions: List[str]
    is_reply: bool
    url: str
    scraped_at: str

class NitterSeleniumScraper:
    def __init__(self, config: Dict):
        self.config = config
        self.instances = config.get("nitter_instances", ["https://nitter.net"])
        self.headless = config.get("headless", False)
        self.min_sleep = config.get("min_sleep", 2.5)
        self.max_sleep = config.get("max_sleep", 6.5)
        self.per_tag_target = config.get("per_tag_target", 500)
        self.max_scrolls = config.get("max_scrolls_per_tag", 50)
        self.driver = self._init_driver()
        self.instance = self._select_working_instance()
        self.seen: Set[str] = set()
        logger.info(f"Using instance: {self.instance}")

    def _init_driver(self):
        opts = uc.ChromeOptions()
        if self.headless:
            opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_argument("--window-size=1920,1080")
        opts.add_argument("--incognito")
        driver = uc.Chrome(options=opts)
        driver.set_page_load_timeout(60)
        driver.set_script_timeout(60)
        return driver

    def _is_reachable(self, url: str, timeout: float = 2.0) -> bool:
        try:
            host = url.replace("https://", "").replace("http://", "").split("/")[0]
            socket.create_connection((host, 443), timeout=timeout).close()
            return True
        except Exception:
            return False

    def _select_working_instance(self) -> str:
        for inst in self.instances:
            if self._is_reachable(inst):
                try:
                    self.driver.get(f"{inst}/search?q=%23nifty50&f=tweets")
                    time.sleep(2)
                    html = self.driver.page_source.lower()
                    if "timeline-item" in html or "tweet-content" in html:
                        return inst
                except Exception:
                    continue
        return self.instances[0]

    def _parse_number(self, text: str) -> int:
        if not text:
            return 0
        t = text.strip().upper().replace(",", "")
        try:
            if t.endswith("K"):
                return int(float(t[:-1]) * 1_000)
            if t.endswith("M"):
                return int(float(t[:-1]) * 1_000_000)
            return int(float(t))
        except Exception:
            return 0

    def _extract_tweet_from_element(self, tweet_elem) -> Optional[Tweet]:
        try:
            # nitter structure parsing using BS element
            link = tweet_elem.find("a", class_="tweet-link")
            if not link:
                return None
            href = link.get("href", "")
            if "/status/" not in href:
                return None
            tweet_id = href.split("/status/")[-1].split("/")[0]
            if tweet_id in self.seen:
                return None

            username = (tweet_elem.find("a", class_="username") or {}).get("title", "")
            if username.startswith("@"):
                username = username[1:]
            fullname = tweet_elem.find("a", class_="fullname")
            display_name = fullname.get_text(strip=True) if fullname else username
            content_div = tweet_elem.find("div", class_="tweet-content")
            content = clean_text(content_div.get_text(" ", strip=True)) if content_div else ""
            date_elem = tweet_elem.find("a", class_="tweet-date")
            timestamp = date_elem.get("title", datetime.utcnow().isoformat()) if date_elem else datetime.utcnow().isoformat()

            # stats
            likes = retweets = replies = 0
            stats = tweet_elem.find("div", class_="tweet-stats")
            if stats:
                for s in stats.find_all("span", class_="tweet-stat"):
                    txt = s.get_text(strip=True)
                    if "heart" in str(s) or "icon-heart" in str(s):
                        likes = self._parse_number(txt)
                    elif "retweet" in str(s) or "icon-retweet" in str(s):
                        retweets = self._parse_number(txt)
                    elif "comment" in str(s) or "icon-comment" in str(s):
                        replies = self._parse_number(txt)

            hashtags = parse_hashtags(content)
            mentions = parse_mentions(content)
            is_reply = "replying to" in content.lower()

            tweet = Tweet(
                tweet_id=tweet_id,
                username=username,
                display_name=display_name,
                timestamp=timestamp,
                content=content,
                likes=likes,
                retweets=retweets,
                replies=replies,
                views=0,
                hashtags=hashtags,
                mentions=mentions,
                is_reply=is_reply,
                url=f"https://twitter.com{href}",
                scraped_at=datetime.utcnow().isoformat()
            )
            self.seen.add(tweet_id)
            return tweet
        except Exception as e:
            logger.debug("parse error %s", e)
            return None

    def _load_page_soup(self, url: str, tries=3):
        for i in range(tries):
            try:
                logger.info("GET %s", url)
                self.driver.get(url)
                WebDriverWait(self.driver, 8).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                time.sleep(1.2)
                html = self.driver.page_source
                soup = BeautifulSoup(html, "lxml")
                return soup
            except Exception as e:
                logger.warning("load failed %s -> retrying (%s)", e, i)
                time.sleep(2 + i)
        raise RuntimeError(f"Failed to load {url}")

    def scrape_search(self, query: str, per_tag_target: Optional[int] = None, max_scrolls: Optional[int] = None) -> List[dict]:
        per_tag_target = per_tag_target or self.per_tag_target
        max_scrolls = max_scrolls or self.max_scrolls
        encoded = quote(query)
        url = f"{self.instance}/search?q={encoded}&f=tweets"
        collected = []
        scroll = 0
        while scroll < max_scrolls and len(collected) < per_tag_target:
            soup = self._load_page_soup(url)
            elems = soup.find_all("div", class_="timeline-item")
            logger.info("found %d elements on page", len(elems))
            for e in elems:
                t = self._extract_tweet_from_element(e)
                if t:
                    collected.append(asdict(t))
                    if len(collected) >= per_tag_target:
                        break
            # try to find "show more" next link
            next_link = None
            for a in soup.select("div.show-more a"):
                href = a.get("href", "")
                if "cursor=" in href:
                    next_link = href
                    break
            if not next_link:
                break
            # normalize
            if next_link.startswith("/"):
                url = f"{self.instance}{next_link}"
            elif next_link.startswith("?"):
                url = f"{self.instance}/search{next_link}"
            else:
                url = f"{self.instance}/search?{next_link}"
            # polite cookie clear + sleep
            try:
                self.driver.delete_all_cookies()
            except Exception:
                pass
            backoff_sleep(self.min_sleep, self.max_sleep)
            scroll += 1
        logger.info("collected %d for %s", len(collected), query)
        return collected

    def scrape_hashtags(self, hashtags: List[str], target_count: int = 2000):
        all_tweets = []
        per_tag = max(100, int(target_count / max(1, len(hashtags))))
        for tag in hashtags:
            if len(all_tweets) >= target_count:
                break
            q = f"#{tag}"
            logger.info("scraping tag %s (target %s)", tag, per_tag)
            tlist = self.scrape_search(q, per_tag, self.max_scrolls)
            all_tweets.extend(tlist)
            # random polite pause
            backoff_sleep(self.min_sleep, self.max_sleep)
        # dedupe by tweet_id
        unique = {t["tweet_id"]: t for t in all_tweets}
        return list(unique.values())

    def close(self):
        try:
            self.driver.quit()
        except Exception:
            pass
