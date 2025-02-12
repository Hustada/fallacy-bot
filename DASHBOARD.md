# RhetoricalRef Dashboard Deployment

This is the dashboard component of RhetoricalRef, allowing users to test and explore the fallacy detection capabilities without needing Twitter access.

## Deployment Instructions

1. Go to [Streamlit Cloud](https://share.streamlit.io)
2. Connect your GitHub repository
3. Deploy using these settings:
   - Main file path: `bot/dashboard/app.py`
   - Requirements: `requirements-dashboard.txt`

## Environment Variables Required

Add these in Streamlit Cloud's secrets management:
```toml
[openai]
OPENAI_API_KEY = "your-api-key"
```
