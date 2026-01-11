# Field Support

A chat interface for Peter McEwen with web search capabilities and streaming responses.

## Features

- **Chat Interface:** Conversational AI assistant with Peter's voice and style
- **Streaming Responses:** Real-time text streaming via Server-Sent Events
- **Web Search:** Automatic web search for current information when needed
- **Model Selection:** Choose between Sonnet (fast) or Opus (smart)
- **Export Chat:** Download conversations as markdown files
- **Resource Management:** Upload and manage instruction files and reference materials
- **Custom Fonts:** GT Alpina, GT America, and GT America Mono typography

## Setup (Local)

### 1. Prerequisites

- Python 3.9 or higher
- An Anthropic API key ([get one here](https://console.anthropic.com/))

### 2. Clone or download this folder

Put the project folder wherever you keep projects.

### 3. Create a virtual environment (recommended)

```bash
cd Field-Admin-Voice
python3 -m venv venv
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

Then edit `.env` and replace the placeholder with your actual API key.

Alternatively, export it directly:

```bash
export ANTHROPIC_API_KEY=sk-ant-your-actual-key
```

### 6. Run the app

```bash
python3 app.py
```

Open your browser to `http://localhost:5001`

## Usage

1. **Type a message** in the text area and press Enter to send
2. **Select model** using the dropdown (Sonnet for speed, Opus for complex tasks)
3. **Export** your conversation as a markdown file
4. **Resources** button to manage instruction files and reference materials

## Customizing

### Instructions (Behavior Rules)

Add `.md` files to `prompts/instructions/` to define behavior rules. These are loaded first in the system prompt.

### Resource Files

Add `.md` files to `prompts/` (root level) to provide reference materials like voice guides, FAQs, or example content.

Changes take effect on the next message (no restart needed).

## File Structure

```
Field-Admin-Voice/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── .env.example          # Template for environment variables
├── .env                  # Your actual API key (don't commit this)
├── templates/
│   └── index.html        # Web interface
├── static/
│   └── fonts/            # Custom font files (.otf)
└── prompts/
    ├── instructions/     # Behavior rules (.md files)
    └── *.md              # Resource files
```

## Deployment

### Replit

1. Import the GitHub repo
2. Add `ANTHROPIC_API_KEY` in Secrets
3. Run

### Other Platforms (Railway, Render, etc.)

1. Connect to Git repo
2. Add `ANTHROPIC_API_KEY` environment variable
3. Use `gunicorn app:app` as the start command

## Costs

Uses the Claude API (pay-per-use). Sonnet is more cost-effective for most tasks; Opus is available for complex reasoning.

## Troubleshooting

**"Error: Could not find API key"**
Make sure you've set `ANTHROPIC_API_KEY` either in `.env` or as an environment variable.

**"Error: rate_limit_error"**
You've hit usage limits. Check your Anthropic dashboard.

**Port already in use**
Kill the existing process: `lsof -ti:5001 | xargs kill -9`
