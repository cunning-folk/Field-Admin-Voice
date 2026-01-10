"""
Peter McEwen Field Assistant
A chat interface with web search capabilities.
"""

from flask import Flask, render_template, request, jsonify
from anthropic import Anthropic
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import os
import requests
from pathlib import Path

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Load API key from environment
client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# Web search tool definition
WEB_SEARCH_TOOL = {
    "name": "web_search",
    "description": "Search the web for current information. Use this when you need up-to-date information, facts you're unsure about, or when the user asks about recent events, people, companies, or topics that may have changed since your knowledge cutoff.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query to look up"
            }
        },
        "required": ["query"]
    }
}

def perform_web_search(query):
    """Perform a web search using DuckDuckGo's instant answer API."""
    try:
        # Use DuckDuckGo instant answer API (free, no key needed)
        response = requests.get(
            "https://api.duckduckgo.com/",
            params={
                "q": query,
                "format": "json",
                "no_html": 1,
                "skip_disambig": 1
            },
            timeout=10
        )
        data = response.json()

        results = []

        # Get abstract/summary if available
        if data.get("Abstract"):
            results.append(f"Summary: {data['Abstract']}")
            if data.get("AbstractSource"):
                results.append(f"Source: {data['AbstractSource']}")

        # Get related topics
        if data.get("RelatedTopics"):
            results.append("\nRelated information:")
            for topic in data["RelatedTopics"][:5]:
                if isinstance(topic, dict) and topic.get("Text"):
                    results.append(f"- {topic['Text']}")

        # Get instant answer if available
        if data.get("Answer"):
            results.insert(0, f"Answer: {data['Answer']}")

        if results:
            return "\n".join(results)
        else:
            return f"No detailed results found for '{query}'. Try rephrasing the search or ask me to search for something more specific."

    except Exception as e:
        return f"Search error: {str(e)}"

# Prompts directory
PROMPTS_DIR = Path(__file__).parent / "prompts"

def get_all_prompt_files():
    """Get all .md files from the prompts directory."""
    if not PROMPTS_DIR.exists():
        PROMPTS_DIR.mkdir(parents=True)
    return sorted(PROMPTS_DIR.glob("*.md"))

def build_system_prompt():
    """Construct the full system prompt from all .md files in prompts/."""
    prompt_files = get_all_prompt_files()

    resources = []
    for file_path in prompt_files:
        name = file_path.stem.replace("_", " ").title()
        content = file_path.read_text()
        resources.append(f"## {name}\n\n{content}")

    resources_text = "\n\n".join(resources) if resources else "(No resource files loaded)"

    return f"""You are an AI assistant for Peter McEwen, founder of The Field.

You help Peter with various tasks including drafting emails, answering questions, research, and providing advice—all in Peter's voice and style.

When writing as Peter, make it sound like he wrote it quickly and naturally—not like an AI wrote it carefully.

You have access to web search. Use it when:
- Asked about current events, news, or recent information
- Looking up facts about people, companies, or organizations
- Researching topics you're unsure about
- The user explicitly asks you to search or look something up

{resources_text}

Match the appropriate length and depth to the type of request. Keep responses concise unless depth is needed.
"""

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/files", methods=["GET"])
def list_files():
    """List all .md files in the prompts directory."""
    files = [f.name for f in get_all_prompt_files()]
    return jsonify({"files": files})

@app.route("/upload", methods=["POST"])
def upload_file():
    """Upload a .md file to the prompts directory."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not file.filename.endswith(".md"):
        return jsonify({"error": "Only .md files are allowed"}), 400

    filename = secure_filename(file.filename)
    file_path = PROMPTS_DIR / filename
    file.save(file_path)

    return jsonify({"success": True, "filename": filename})

@app.route("/delete/<filename>", methods=["DELETE"])
def delete_file(filename):
    """Delete a .md file from the prompts directory."""
    filename = secure_filename(filename)
    file_path = PROMPTS_DIR / filename

    if not file_path.exists():
        return jsonify({"error": "File not found"}), 404

    file_path.unlink()
    return jsonify({"success": True})

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    messages = data.get("messages", [])

    if not messages:
        return jsonify({"error": "No messages provided"}), 400

    try:
        # Rebuild system prompt each time to pick up new files
        system_prompt = build_system_prompt()

        # Initial API call with tools
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=system_prompt,
            messages=messages,
            tools=[WEB_SEARCH_TOOL]
        )

        # Handle tool use loop
        tool_uses = []
        while response.stop_reason == "tool_use":
            # Find tool use blocks
            tool_use_block = None
            for block in response.content:
                if block.type == "tool_use":
                    tool_use_block = block
                    break

            if not tool_use_block:
                break

            # Execute the search
            search_query = tool_use_block.input.get("query", "")
            tool_uses.append(search_query)
            search_results = perform_web_search(search_query)

            # Add assistant's response and tool result to messages
            messages = messages + [
                {"role": "assistant", "content": response.content},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use_block.id,
                            "content": search_results
                        }
                    ]
                }
            ]

            # Get next response
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                system=system_prompt,
                messages=messages,
                tools=[WEB_SEARCH_TOOL]
            )

        # Extract final text response
        reply = ""
        for block in response.content:
            if hasattr(block, "text"):
                reply += block.text

        return jsonify({
            "reply": reply,
            "searches": tool_uses  # Let frontend know what was searched
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(debug=True, host="0.0.0.0", port=port)
