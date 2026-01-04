import yfinance as yf
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import warnings

warnings.filterwarnings("ignore")

class NewsSentimentEngine:
    def __init__(self):
        self.vader = SentimentIntensityAnalyzer()

    def get_sentiment(self, ticker):
        """
        Fetches official news from Yahoo Finance for a given ticker.
        Returns: Average Compound Score (-1 to 1), Count of articles, Top Headline
        """
        try:
            # Ticker object
            stock = yf.Ticker(ticker)
            news_list = stock.news
            
            if not news_list:
                return 0.0, 0, "No news found."

            total_score = 0
            count = 0
            headlines = []

            for article in news_list:
                title = article.get('title', '')
                if title:
                    score = self.vader.polarity_scores(title)['compound']
                    total_score += score
                    count += 1
                    headlines.append(title)
            
            if count == 0:
                return 0.0, 0, "No valid headlines."

            avg_score = total_score / count
            top_headline = headlines[0] if headlines else "N/A"
            
            return avg_score, count, top_headline

        except Exception as e:
            # Fail gracefully so the bot doesn't crash
            return 0.0, 0, f"Error: {str(e)}"

if __name__ == "__main__":
    # Quick Test
    engine = NewsSentimentEngine()
    score, count, headline = engine.get_sentiment("TATASTEEL.NS")
    print(f"Sentiment: {score} | Articles: {count}")
    print(f"Top Story: {headline}")