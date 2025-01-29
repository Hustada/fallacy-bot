import time
import logging
from bot.twitter_monitor import TwitterMonitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
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
                accounts_to_monitor = ["example_account"]  # Replace with actual accounts
                for account in accounts_to_monitor:
                    logger.info(f"Monitoring account: {account}")
                    monitor.monitor_account(account)
                
                # Wait before next check (5 minutes)
                logger.info("Waiting 5 minutes before next check...")
                time.sleep(300)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                time.sleep(60)  # Wait a minute before retrying
    
    except KeyboardInterrupt:
        logger.info("Shutting down monitor...")
    finally:
        monitor.cleanup()

if __name__ == "__main__":
    main()
