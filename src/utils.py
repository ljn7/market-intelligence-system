import re
import time
import random
from typing import List

def clean_text(text: str) -> str:
    # normalize whitespace and control chars
    t = text.replace("\u200b", " ").replace("\xa0", " ")
    t = re.sub(r"\s+", " ", t).strip()
    return t

def parse_hashtags(text: str) -> List[str]:
    tags = re.findall(r"#\w+", text.lower())
    return list(dict.fromkeys(tags))

def parse_mentions(text: str) -> List[str]:
    mentions = re.findall(r"@\w+", text)
    return list(dict.fromkeys(mentions))

def backoff_sleep(min_s=1.0, max_s=3.0, jitter=True):
    s = random.uniform(min_s, max_s)
    if jitter:
        s = s * random.uniform(0.8, 1.2)
    time.sleep(s)
