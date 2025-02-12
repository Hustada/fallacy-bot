# Deployment Guide

## Local Development

1. Create a `.env` file in the `bot` directory with your OpenAI API key:
```bash
OPENAI_API_KEY=your-key-here
```

2. Run the dashboard:
```bash
cd /Users/markhustad/Projects/python/twitter-fallacy-bot
streamlit run bot/dashboard/app.py
```

## Streamlit Cloud Deployment

1. Go to [share.streamlit.io](https://share.streamlit.io)

2. Connect your GitHub repository (https://github.com/hustada/fallacy-bot)

3. Configure the deployment:
   - Main file path: `bot/dashboard/app.py`
   - Python version: 3.11
   - Requirements file: `requirements-dashboard.txt`

4. Add your secrets:
   - Go to "Advanced Settings" > "Secrets"
   - Copy the contents of `streamlit-secrets-template.toml`
   - Add your OpenAI API key
   ```toml
   [openai]
   OPENAI_API_KEY = "your-key-here"
   ```

5. Deploy!
