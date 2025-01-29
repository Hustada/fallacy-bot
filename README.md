# Fallacy Bot

An AI-powered bot that detects logical fallacies in text and provides educational feedback using GPT-3.5-turbo.

## Features

- 🔍 Advanced fallacy detection using OpenAI's GPT-3.5-turbo
- 🎓 Educational and constructive feedback
- 📊 Interactive dashboard for testing and monitoring
- 🔄 Automatic retry mechanism for API calls
- 📝 Detailed logging for debugging
- 💾 SQLite database for activity tracking

## Supported Fallacies

- Ad Hominem: Attacking the person instead of their argument
- False Dichotomy: Presenting only two options when more exist
- Appeal to Authority: Claiming something is true because an authority said so
- Strawman: Misrepresenting an opponent's argument
- Slippery Slope: Arguing that a small first step will lead to significant negative consequences
- Appeal to Emotion: Using emotions rather than facts to win an argument
- Hasty Generalization: Drawing conclusions from insufficient evidence
- Circular Reasoning: Using the conclusion as a premise
- Bandwagon: Arguing that something is true because many people believe it
- Anecdotal: Using a personal experience or isolated example instead of sound reasoning

## Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/fallacy-bot.git
cd fallacy-bot
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the bot directory with your OpenAI API key:
```
OPENAI_API_KEY=your_openai_api_key
```

5. Run the bot:
```bash
python run.py
```

The dashboard will be available at http://localhost:8501

## Usage

1. Open the dashboard in your browser
2. Navigate to the "Sandbox" tab
3. Enter any text to analyze
4. Click "Analyze" to detect logical fallacies
5. Review the detected fallacies and educational feedback

## Example

Input:
> "Everyone knows that video games cause violence. My neighbor's kid played violent games and got into a fight at school, so that proves it!"

The bot will detect multiple fallacies:
- Bandwagon ("Everyone knows...")
- Anecdotal (using a single case as proof)
- Hasty Generalization (drawing conclusions from insufficient evidence)

## Development

- Built with Python 3.13
- Uses Streamlit for the dashboard
- SQLite for data storage
- OpenAI API for fallacy detection
- Comprehensive logging for debugging

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - feel free to use this code for your own projects!
