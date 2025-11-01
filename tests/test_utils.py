from src.utils import clean_text, parse_hashtags, parse_mentions

def test_clean():
    s = "hello\u200b world \n new"
    assert " " in clean_text(s)

def test_tags_mentions():
    t = "Hello #Nifty50 check @user and #nifty50 again"
    tags = parse_hashtags(t)
    mentions = parse_mentions(t)
    assert "#nifty50" in tags
    assert "@user" in mentions
