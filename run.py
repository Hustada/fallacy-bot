import subprocess
import sys
import time
import os
from pathlib import Path
from dotenv import load_dotenv
from bot.database.models import init_db

# Load environment variables
project_root = Path(__file__).parent
env_path = project_root / 'bot' / '.env'
load_dotenv(env_path)

# Get the current environment
env = os.environ.copy()

# Get virtual environment paths
venv_path = project_root / 'venv'
if sys.platform == 'win32':
    python_path = venv_path / 'Scripts' / 'python.exe'
else:
    python_path = venv_path / 'bin' / 'python'

def run_ngrok():
    try:
        # Start ngrok
        ngrok_process = subprocess.Popen(
            ['ngrok', 'http', '8000'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env
        )
        time.sleep(3)  # Wait for ngrok to start
        
        # Get the public URL
        ngrok_url = subprocess.check_output(
            ['curl', 'http://localhost:4040/api/tunnels'],
            universal_newlines=True
        )
        return ngrok_process
    except Exception as e:
        print(f"Error starting ngrok: {e}")
        sys.exit(1)

def run_webhook_server():
    try:
        # Start the FastAPI webhook server
        webhook_process = subprocess.Popen(
            [str(python_path), '-m', 'uvicorn', 'bot.webhook_handler:app', '--reload'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env
        )
        return webhook_process
    except Exception as e:
        print(f"Error starting webhook server: {e}")
        sys.exit(1)

def run_dashboard():
    try:
        # Get the absolute path to the dashboard
        dashboard_path = project_root / 'bot' / 'dashboard' / 'app.py'
        
        # Update environment with PYTHONPATH
        dashboard_env = env.copy()
        dashboard_env['PYTHONPATH'] = str(project_root)
        
        print("Starting dashboard...")
        print(f"Python path: {python_path}")
        print(f"Dashboard path: {dashboard_path}")
        print(f"PYTHONPATH: {dashboard_env.get('PYTHONPATH')}")
        
        # Start the Streamlit dashboard using virtual environment's Python
        dashboard_process = subprocess.Popen(
            [str(python_path), '-m', 'streamlit', 'run', str(dashboard_path)],
            env=dashboard_env
        )
        return dashboard_process
    except Exception as e:
        print(f"Error starting dashboard: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Ensure the database exists
    print("Initializing database...")
    init_db()
    
    # Start all services
    print("Starting services...")
    ngrok_process = run_ngrok()
    webhook_process = run_webhook_server()
    dashboard_process = run_dashboard()
    
    try:
        # Keep the script running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down services...")
        ngrok_process.terminate()
        webhook_process.terminate()
        dashboard_process.terminate()
        sys.exit(0)
