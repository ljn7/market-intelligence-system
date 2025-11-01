import logging
import numpy as np
from typing import List, Dict

logger = logging.getLogger(__name__)

def build_composite_signal(tweets: List[Dict], tfidf_vect, tfidf_matrix, top_k=25):
    # Create a naive composite score per tweet = sum of TF-IDF values (sparse sums).
    if tfidf_matrix is None:
        return []
    row_sums = np.asarray(tfidf_matrix.sum(axis=1)).ravel()
    # normalize
    if row_sums.max() > 0:
        norm = row_sums / (row_sums.max())
    else:
        norm = row_sums
    results = []
    for i, t in enumerate(tweets):
        results.append({
            "tweet_id": t.get("tweet_id"),
            "username": t.get("username"),
            "score": float(norm[i]),
            "content": t.get("content", "")[:280]
        })
    # top signals
    top = sorted(results, key=lambda x: x["score"], reverse=True)[:top_k]
    return {"top_signals": top, "all": results}
