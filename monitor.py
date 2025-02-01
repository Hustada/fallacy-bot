import time
import logging
import os
from pathlib import Path
from dotenv import load_dotenv
from bot.twitter_monitor_playwright import TwitterMonitorPlaywright
import asyncio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    # Load environment variables from the bot directory
    env_path = Path(__file__).parent / 'bot' / '.env'
    logger.info(f"Loading .env file from: {env_path}")
    logger.info(f"File exists: {env_path.exists()}")
    
    load_dotenv(env_path)
    
    # Debug: Check if API key is loaded
    api_key = os.getenv("OPENAI_API_KEY")
    logger.info(f"API key loaded: {bool(api_key)}")
    if not api_key:
        logger.error("OpenAI API key not found in environment!")
        logger.info("Current environment variables:")
        for key in os.environ:
            if 'KEY' in key or 'TOKEN' in key:
                logger.info(f"Found key: {key}")
    
    monitor = TwitterMonitorPlaywright()
    
    try:
        # Start the monitor
        await monitor.setup()
        
        while True:
            try:
                # Check notifications
                logger.info("Checking notifications...")
                # Removed monitor.check_notifications() as it's not present in the updated code
               
                # Monitor specific accounts (add accounts you want to monitor)
                accounts_to_monitor = ["krassenstein", "RpsAgainstTrump", "ConceptualJames", "mhdksafa", "Mollyploofkins", "AesPolitics1", "ContinuumCritic", "hustadvicka"] # Replace with actual accounts
                for account in accounts_to_monitor:
                    logger.info(f"Monitoring account: {account}")
                    await monitor.monitor_account(account)
                
                # Wait before next check (30 seconds)
                logger.info("Waiting 30 seconds before next check...")
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                await asyncio.sleep(60)  # Wait a minute before retrying
    
    except KeyboardInterrupt:
        logger.info("Shutting down monitor...")
    finally:
        await monitor.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
