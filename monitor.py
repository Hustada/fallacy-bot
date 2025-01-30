import time
import logging
import os
from pathlib import Path
from dotenv import load_dotenv
from bot.twitter_monitor import TwitterMonitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    # Load environment variables from the bot directory
    env_path = Path(__file__).parent / 'bot' / '.env'
    load_dotenv(env_path)
    
    monitor = TwitterMonitor()
    
    try:
        # Start the monitor
        monitor.start()
        
        while True:
            try:
                # Check notifications
                logger.info("Checking notifications...")
                monitor.check_notifications()
                
                # Monitor specific accounts (add accounts you want to monitor)
                accounts_to_monitor = ["hustadvicka", "continuumcritic"]  # Replace with actual accounts
                for account in accounts_to_monitor:
                    logger.info(f"Monitoring account: {account}")
                    monitor.monitor_account(account)
                
                # Wait before next check (30 seconds)
                logger.info("Waiting 30 seconds before next check...")
                time.sleep(30)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                time.sleep(60)  # Wait a minute before retrying
    
    except KeyboardInterrupt:
        logger.info("Shutting down monitor...")
    finally:
        monitor.cleanup()

if __name__ == "__main__":
    main()
