import sqlite3
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class DBManager:
    def __init__(self, db_path="bot/tweets.db"):
        self.db_path = db_path
        self.setup_database()

    def setup_database(self):
        """Create the database and tables if they don't exist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS processed_tweets (
                        tweet_id TEXT PRIMARY KEY,
                        processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        account TEXT
                    )
                """)
                conn.commit()
                logger.info("Database setup successfully")
        except Exception as e:
            logger.error(f"Error setting up database: {e}")

    def is_tweet_processed(self, tweet_id: str) -> bool:
        """Check if we've already processed this tweet."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM processed_tweets WHERE tweet_id = ?", (tweet_id,))
                result = cursor.fetchone() is not None
                logger.info(f"Checking tweet {tweet_id}: {'already processed' if result else 'not processed'}")
                return result
        except Exception as e:
            logger.error(f"Error checking tweet status: {e}")
            return False

    def mark_tweet_processed(self, tweet_id: str, account: str):
        """Mark a tweet as processed."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO processed_tweets (tweet_id, account) VALUES (?, ?)",
                    (tweet_id, account)
                )
                conn.commit()
                logger.info(f"Successfully marked tweet {tweet_id} from account {account} as processed")
        except sqlite3.IntegrityError:
            logger.warning(f"Tweet {tweet_id} was already marked as processed (duplicate entry)")
        except Exception as e:
            logger.error(f"Error marking tweet as processed: {e}")

    def cleanup_old_entries(self, days=30):
        """Remove entries older than specified days."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM processed_tweets WHERE processed_at < ?",
                    (datetime.now() - timedelta(days=days),)
                )
                conn.commit()
                logger.info(f"Cleaned up old entries older than {days} days")
        except Exception as e:
            logger.error(f"Error cleaning up old entries: {e}")
