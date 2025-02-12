# Deployment Guide

## Local Development

1. Clone the repository:
   ```bash
   git clone https://github.com/Hustada/fallacy-bot.git
   cd fallacy-bot
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the `bot` directory with your OpenAI API key:
   ```bash
   OPENAI_API_KEY=your-key-here
   ```

5. Run the dashboard:
   ```bash
   streamlit run bot/dashboard/app.py
   ```

## Streamlit Cloud Deployment

1. Go to [share.streamlit.io](https://share.streamlit.io/)

2. Click "New app" and select your repository:
   - Repository: `Hustada/fallacy-bot`
   - Branch: `feature/twitter-monitor`
   - Main file path: `bot/dashboard/app.py`
   - Python version: `3.11`

3. Add your OpenAI API key in Streamlit secrets:
   - Click "Advanced settings" ⚙️
   - Under "Secrets", add:
     ```toml
     [openai]
     OPENAI_API_KEY = "your-key-here"
     ```

4. Click "Deploy!"

Your dashboard will be live at: `https://fallacy-bot.streamlit.app` (or similar URL provided by Streamlit)

## Troubleshooting

If you encounter any issues:
1. Check the app logs in Streamlit Cloud
2. Verify your OpenAI API key is correctly set in Streamlit secrets
3. Make sure all dependencies are properly installed (they're all in `requirements.txt`)
