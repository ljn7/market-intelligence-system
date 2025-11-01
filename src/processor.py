from sklearn.feature_extraction.text import TfidfVectorizer
from typing import List, Tuple
import numpy as np
import logging

logger = logging.getLogger(__name__)

def prepare_corpus(tweets: List[dict]) -> List[str]:
    texts = []
    for t in tweets:
        text = t.get("content", "")
        texts.append(text)
    return texts

def compute_tfidf_features(texts: List[str], max_features=10000, ngram_range=(1,2)):
    vect = TfidfVectorizer(max_features=max_features, ngram_range=ngram_range, analyzer="word")
    X = vect.fit_transform(texts)
    logger.info("TF-IDF matrix shape: %s", X.shape)
    return vect, X

def aggregate_signal_from_tfidf(X, vectorizer, top_k=20):
    import numpy as np
    sums = np.asarray(X.sum(axis=0)).ravel()
    idx = sums.argsort()[::-1][:top_k]
    features = np.array(vectorizer.get_feature_names_out())[idx]
    weights = sums[idx] / (sums.max() + 1e-12)
    signals = list(zip(features.tolist(), weights.tolist()))
    return signals
