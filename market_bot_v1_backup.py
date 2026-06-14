import os
import feedparser
import yfinance as yf
import pandas as pd
import smtplib
import ssl

from email.mime.text import MIMEText
from datetime import datetime

EMAIL_ADDRESS = os.environ["EMAIL_ADDRESS"]
EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]

SYMBOLS = {
    "NIFTY": "^NSEI",
    "BANKNIFTY": "^NSEBANK",
    "RELIANCE": "RELIANCE.NS",
    "INFY": "INFY.NS",
    "SENSEX": "^BSESN"
}

RSS_FEEDS = [
    "https://indianexpress.com/feed/",
    "https://feeds.reuters.com/reuters/businessNews",
    "https://finance.yahoo.com/rss/topstories"
]

POSITIVE_WORDS = [
    "growth",
    "profit",
    "surge",
    "gain",
    "strong",
    "bullish",
    "rise",
    "record"
]

NEGATIVE_WORDS = [
    "loss",
    "decline",
    "fall",
    "crash",
    "weak",
    "bearish",
    "drop"
]

def collect_news():
    headlines = []

    for feed in RSS_FEEDS:
        try:
            parsed = feedparser.parse(feed)

            for entry in parsed.entries[:10]:
                title = entry.get("title", "")

                if title:
                    headlines.append(title)

        except Exception:
            pass

    return headlines

def sentiment_score(text):
    text = text.lower()

    positive = sum(word in text for word in POSITIVE_WORDS)
    negative = sum(word in text for word in NEGATIVE_WORDS)

    return positive - negative

def analyze_news():
    headlines = collect_news()

    if not headlines:
        return 0, "No news available"

    scores = [sentiment_score(h) for h in headlines]

    average_score = sum(scores) / len(scores)

    summary = "\n".join(headlines[:10])

    return average_score, summary

def analyze_symbol(name, ticker):
    try:
        data = yf.download(
            ticker,
            period="6mo",
            progress=False
        )

        if data.empty:
            return None

        close = data["Close"]

        sma20 = close.rolling(20).mean()
        sma50 = close.rolling(50).mean()

        latest_price = float(close.iloc[-1])

        trend = "BULLISH"

        if sma20.iloc[-1] < sma50.iloc[-1]:
            trend = "BEARISH"

        return {
            "symbol": name,
            "price": round(latest_price, 2),
            "trend": trend
        }

    except Exception:
        return None

def send_email(report_text):
    message = MIMEText(report_text)

    message["Subject"] = "AI Market Research Report"
    message["From"] = EMAIL_ADDRESS
    message["To"] = EMAIL_ADDRESS

    context = ssl.create_default_context()

    with smtplib.SMTP_SSL(
        "smtp.gmail.com",
        465,
        context=context
    ) as server:

        server.login(
            EMAIL_ADDRESS,
            EMAIL_PASSWORD
        )

        server.sendmail(
            EMAIL_ADDRESS,
            EMAIL_ADDRESS,
            message.as_string()
        )

def main():
    news_score, news_summary = analyze_news()

    report_lines = []

    report_lines.append("AI MARKET RESEARCH REPORT")
    report_lines.append(str(datetime.now()))
    report_lines.append("")
    report_lines.append("NEWS SCORE: " + str(news_score))
    report_lines.append("")
    report_lines.append("HEADLINES:")
    report_lines.append(news_summary)
    report_lines.append("")

    results = []

    for name, ticker in SYMBOLS.items():
        result = analyze_symbol(name, ticker)

        if result is not None:
            results.append(result)

    for item in results:
        report_lines.append(
            f"{item['symbol']} | {item['trend']} | Price: {item['price']}"
        )

    report_text = "\n".join(report_lines)

    print(report_text)

    pd.DataFrame(results).to_csv(
        "latest_report.csv",
        index=False
    )

    send_email(report_text)

if __name__ == "__main__":
    main()
