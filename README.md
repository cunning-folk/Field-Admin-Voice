# The Field Email Assistant

A simple web interface for drafting email responses in Peter's voice.

## What This Does

Paste an incoming email, click a button, get a draft response written in Peter's voice. The system uses Claude's API with a custom system prompt that includes:

- Peter's voice guide (tone, vocabulary, patterns to avoid)
- Example emails Peter has actually written
- Instructions for handling different types of inquiries

## Setup (Local)

### 1. Prerequisites

- Python 3.9 or higher
- An Anthropic API key ([get one here](https://console.anthropic.com/))

### 2. Clone or download this folder

Put the `email-assistant` folder wherever you keep projects.

### 3. Create a virtual environment (recommended)

```bash
cd email-assistant
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Set up your API key

Copy the example environment file and add your key:

```bash
cp .env.example .env
```

Then edit `.env` and replace `sk-ant-xxxxxxxxxxxxx` with your actual API key.

Alternatively, export it directly:

```bash
export ANTHROPIC_API_KEY=sk-ant-your-actual-key
```

### 6. Run the app

```bash
python app.py
```

Open your browser to `http://localhost:5000`

## Usage

1. **Context (optional):** Add any relevant context about the sender. E.g., "Returning student from Tummo I" or "First inquiry, found us via podcast."

2. **Incoming Email:** Paste the email you're responding to.

3. **Generate Draft:** Click the button. Wait a few seconds.

4. **Review and Edit:** The draft appears in the output box. Copy it, tweak as needed, send.

## Customizing

### Voice Guide

Edit `prompts/voice_guide.md` to adjust the voice instructions. Changes take effect on next server restart.

### Example Emails

Edit `prompts/example_emails.md` to add more examples or update existing ones. More examples = better pattern matching.

### Model

The app uses `claude-sonnet-4-20250514` by default. To change it, edit the `model` parameter in `app.py`.

## File Structure

```
email-assistant/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── .env.example          # Template for environment variables
├── .env                  # Your actual API key (don't commit this)
├── templates/
│   └── index.html        # Web interface
└── prompts/
    ├── voice_guide.md    # Peter's voice instructions
    └── example_emails.md # Reference emails
```

## Deploying for Remote Access

If your assistant needs to access this remotely, you'll need to deploy it somewhere. Options:

- **Replit:** Import this folder, add your API key as a Secret, run.
- **Railway/Render:** Connect to a Git repo, add environment variable, deploy.
- **Heroku:** Similar process with their CLI.

For any of these, make sure your API key is set as an environment variable, not committed to code.

## Costs

This uses the Claude API, which is pay-per-use. A typical email draft (including the system prompt) runs about 3,000-4,000 tokens input, 200-500 tokens output. At current Sonnet pricing, that's roughly $0.01-0.02 per draft.

## Troubleshooting

**"Error: Could not find API key"**
Make sure you've set `ANTHROPIC_API_KEY` either in `.env` or as an environment variable.

**"Error: rate_limit_error"**
You've hit usage limits. Check your Anthropic dashboard.

**Drafts sound too generic**
The voice guide or examples might need updating. Review `prompts/` and add more examples of Peter's actual writing.
