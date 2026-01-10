"""
Peter McEwen Email Assistant
A simple web interface for drafting emails in Peter's voice.
"""

from flask import Flask, render_template, request, jsonify
from anthropic import Anthropic
from dotenv import load_dotenv
import os
from pathlib import Path

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Load API key from environment
client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

def load_file(filename):
    """Load a text file from the prompts directory."""
    path = Path(__file__).parent / "prompts" / filename
    if path.exists():
        return path.read_text()
    return ""

def build_system_prompt():
    """Construct the full system prompt from component files."""
    voice_guide = load_file("voice_guide.md")
    example_emails = load_file("example_emails.md")
    
    return f"""You are drafting email responses on behalf of Peter McEwen, founder of The Field.

Your job is to write emails that sound like Peter wrote them quickly and naturally—not like an AI wrote them carefully.

## Voice Guide

{voice_guide}

## Reference: Peter's Actual Emails

Use these as examples of his voice, length, and how he handles different types of questions:

{example_emails}

## Your Task

When given an incoming email, draft a response in Peter's voice. Match the appropriate length and depth to the type of inquiry. Logistics get short responses. Substantive practice questions get real responses.

Do not explain what you're doing. Just write the email response, ready to send (or lightly edit).
"""

SYSTEM_PROMPT = build_system_prompt()

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/draft", methods=["POST"])
def draft_email():
    data = request.json
    incoming_email = data.get("email", "")
    context = data.get("context", "")  # Optional: any context about the sender
    
    user_message = f"Incoming email:\n\n{incoming_email}"
    if context:
        user_message = f"Context about sender: {context}\n\n{user_message}"
    
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": user_message}
            ]
        )
        
        draft = response.content[0].text
        return jsonify({"draft": draft})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
