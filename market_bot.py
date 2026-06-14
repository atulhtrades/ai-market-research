import os
import feedparser
import yfinance as yf
import pandas as pd
import numpy as np
import pytz
import smtplib
import ssl

from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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
"growth","profit","surge","gain","strong",
"bullish","rise","record"
]

NEGATIVE_WORDS = [
"loss","decline","fall","crash",
"weak","bearish","drop"
]

def collect_news():
headlines = []

for feed in RSS_FEEDS:
    try:
        parsed = feedparser.parse(feed)

        for entry in parsed.entries[:10]:
            title = entry.get("title","")

            if title:
                headlines.append(title)

    except:
        pass

return headlines

def sentiment_score(text):

text = text.lower()

pos = sum(word in text for word in POSITIVE_WORDS)
neg = sum(word in text for word in NEGATIVE_WORDS)

return pos - neg

def analyze_news():

headlines = collect_news()

if not headlines:
    return 0,"No headlines available"

scores = [
    sentiment_score(h)
    for h in headlines
]

avg = np.mean(scores)

summary = "\n".join(headlines[:10])

return avg,summary

def calculate_rsi(series, period=14):

delta = series.diff()

gain = delta.where(delta > 0,0)

loss = -delta.where(delta < 0,0)

avg_gain = gain.rolling(period).mean()

avg_loss = loss.rolling(period).mean()

rs = avg_gain / avg_loss

rsi = 100 - (100/(1+rs))

return rsi

def analyze_symbol(name,symbol,news_score):

data = yf.download(
    symbol,
    period="6mo",
    progress=False
)

close = data["Close"]

sma20 = close.rolling(20).mean()

sma50 = close.rolling(50).mean()

rsi = calculate_rsi(close)

price = float(close.iloc[-1])

score = 0

reasons = []

if sma20.iloc[-1] > sma50.iloc[-1]:
    score += 1
    reasons.append("SMA20 above SMA50")
else:
    score -= 1
    reasons.append("SMA20 below SMA50")

if rsi.iloc[-1] > 60:
    score += 1
    reasons.append("Strong RSI")

elif rsi.iloc[-1] < 40:
    score -= 1
    reasons.append("Weak RSI")

if news_score > 0:
    score += 1
    reasons.append("Positive News")

elif news_score < 0:
    score -= 1
    reasons.append("Negative News")

if score >= 2:
    bias = "BULLISH"
    confidence = "HIGH"

elif score <= -2:
    bias = "BEARISH"
    confidence = "HIGH"

else:
    bias = "NEUTRAL"
    confidence = "LOW"

return {
    "Symbol": name,
    "Price": round(price,2),
    "Bias": bias,
    "Confidence": confidence,
    "Reason": ", ".join(reasons)
}

def send_email(report):

msg = MIMEMultipart()

msg["From"] = EMAIL_ADDRESS
msg["To"] = EMAIL_ADDRESS
msg["Subject"] = "AI Market Research Report"

msg.attach(
    MIMEText(report,"plain")
)

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

    server.send_message(msg)

def main():

news_score,news_summary = analyze_news()

report = []

report.append(
    "AI MARKET RESEARCH REPORT"
)

report.append(
    str(datetime.now())
)

report.append("")
report.append("NEWS SUMMARY")
report.append(news_summary)
report.append("")

rows = []

for name,symbol in SYMBOLS.items():

    result = analyze_symbol(
        name,
        symbol,
        news_score
    )

    rows.append(result)

    report.append(
        f"Symbol: {result['Symbol']}"
    )

    report.append(
        f"Price: {result['Price']}"
    )

    report.append(
        f"Bias: {result['Bias']}"
    )

    report.append(
        f"Confidence: {result['Confidence']}"
    )

    report.append(
        f"Reason: {result['Reason']}"
    )

    report.append("")

pd.DataFrame(rows).to_csv(
    "latest_report.csv",
    index=False
)

report_text = "\n".join(report)

print(report_text)

send_email(report_text)

if name == "main":
main()
