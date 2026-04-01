"""
Peter McEwen Field Assistant
A chat interface with web search capabilities.
"""

from flask import Flask, render_template, request, jsonify, Response, session, redirect, url_for
from anthropic import Anthropic
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from functools import wraps
from collections import defaultdict
import os
import json
import re
import time
import requests
from pathlib import Path

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-key-change-in-production")
app.config.update(
    SESSION_COOKIE_SECURE=os.environ.get("FLASK_DEBUG", "false").lower() != "true",
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)

# Rate limiting: max requests per session per minute
RATE_LIMIT = int(os.environ.get("RATE_LIMIT", "10"))
RATE_WINDOW = 60  # seconds
_rate_store = defaultdict(list)

def check_rate_limit():
    """Check if the current session has exceeded the rate limit."""
    session_id = session.get("_id", request.remote_addr)
    now = time.time()
    # Clean old entries
    _rate_store[session_id] = [t for t in _rate_store[session_id] if now - t < RATE_WINDOW]
    if len(_rate_store[session_id]) >= RATE_LIMIT:
        return False
    _rate_store[session_id].append(now)
    return True

# Load API key from environment
client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# Available models
MODELS = {
    "sonnet": "claude-sonnet-4-20250514",
    "opus": "claude-opus-4-20250514"
}
DEFAULT_MODEL = "sonnet"
MAX_TOKENS = 4096

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

# Resource file tool definition (for lazy-loading)
READ_RESOURCE_TOOL = {
    "name": "read_resource",
    "description": "Read a resource file to get reference material like voice guides, example emails, brand values, course information, etc. Use this when you need specific context from The Field's documentation to answer accurately. Available resources will be listed in the system prompt.",
    "input_schema": {
        "type": "object",
        "properties": {
            "filename": {
                "type": "string",
                "description": "The filename of the resource to read (e.g., 'voice_guide.md')"
            }
        },
        "required": ["filename"]
    }
}

def read_resource_file(filename):
    """Read a resource file from the prompts directory."""
    try:
        # Security: only allow reading from prompts directory
        safe_filename = secure_filename(filename)
        file_path = PROMPTS_DIR / safe_filename

        if not file_path.exists():
            return f"Resource file '{filename}' not found. Available files: {', '.join(f.name for f in get_resource_files())}"

        content = file_path.read_text()
        return content
    except Exception as e:
        return f"Error reading resource: {str(e)}"

def perform_web_search(query):
    """Perform a web search using DuckDuckGo HTML search for real results."""
    try:
        # Use DuckDuckGo HTML endpoint for actual search results
        response = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers={"User-Agent": "Mozilla/5.0 (compatible; FieldAssistant/1.0)"},
            timeout=10
        )
        response.raise_for_status()

        # Parse results from HTML (simple extraction without extra deps)
        html = response.text
        results = []
        # Each result has a title in <a class="result__a"> and snippet in <a class="result__snippet">
        titles = re.findall(r'<a[^>]*class="result__a"[^>]*>(.*?)</a>', html)
        snippets = re.findall(r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL)
        urls = re.findall(r'<a[^>]*class="result__url"[^>]*href="([^"]*)"', html)

        # Clean HTML tags from extracted text
        def clean_html(text):
            return re.sub(r'<[^>]+>', '', text).strip()

        for i in range(min(5, len(titles))):
            title = clean_html(titles[i])
            snippet = clean_html(snippets[i]) if i < len(snippets) else ""
            url = urls[i] if i < len(urls) else ""
            result = f"**{title}**"
            if url:
                result += f"\n  URL: {url}"
            if snippet:
                result += f"\n  {snippet}"
            results.append(result)

        if results:
            return f"Search results for '{query}':\n\n" + "\n\n".join(results)

        # Fallback to instant answer API if HTML parsing fails
        fallback = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
            timeout=10
        )
        data = fallback.json()
        if data.get("Abstract"):
            return f"Summary: {data['Abstract']}\nSource: {data.get('AbstractSource', 'N/A')}"

        return f"No results found for '{query}'. Try rephrasing the search."

    except Exception as e:
        return f"Search error: {str(e)}"

# Prompts directories
PROMPTS_DIR = Path(__file__).parent / "prompts"
INSTRUCTIONS_DIR = PROMPTS_DIR / "instructions"


def login_required(f):
    """Decorator to require login for protected routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

def get_instructions():
    """Get all .md files from the instructions directory (behavior rules)."""
    if not INSTRUCTIONS_DIR.exists():
        INSTRUCTIONS_DIR.mkdir(parents=True)
    return sorted(INSTRUCTIONS_DIR.glob("*.md"))

def get_resource_files():
    """Get all .md files from the prompts directory (not in subdirectories)."""
    if not PROMPTS_DIR.exists():
        PROMPTS_DIR.mkdir(parents=True)
    return sorted([f for f in PROMPTS_DIR.glob("*.md") if f.is_file()])

def build_system_prompt():
    """Construct the system prompt with instructions only. Resources are lazy-loaded via tool."""
    # Load instructions (behavior rules) first
    instructions = []
    for file_path in get_instructions():
        content = file_path.read_text()
        instructions.append(content)

    instructions_text = "\n\n".join(instructions) if instructions else ""

    # List available resource files (but don't load content)
    resource_files = get_resource_files()
    resource_list = "\n".join([f"- {f.name}" for f in resource_files]) if resource_files else "(No resource files available)"

    # Build the system prompt with instructions at the top
    base_prompt = """You are an AI assistant for Peter McEwen, founder of The Field.

You help Peter with various tasks including drafting emails, answering questions, research, and providing advice—all in Peter's voice and style.

When writing as Peter, make it sound like he wrote it quickly and naturally—not like an AI wrote it carefully.

You have access to two tools:

1. **web_search**: Use when you need current information, facts about people/companies, or when the user asks you to look something up.

2. **read_resource**: Use to load reference material when you need specific context about The Field's voice, brand, courses, or examples. Load resources BEFORE drafting content that needs to match Peter's style or contain accurate course/program details."""

    # Add instructions if they exist
    if instructions_text:
        base_prompt = f"{base_prompt}\n\n# Instructions\n\n{instructions_text}"

    return f"""{base_prompt}

# Available Resources (use read_resource tool to load)

{resource_list}

Match the appropriate length and depth to the type of request. Keep responses concise unless depth is needed.
"""

@app.route("/login", methods=["GET", "POST"])
def login():
    """Login page and authentication."""
    if request.method == "POST":
        password = request.form.get("password")
        if password == os.environ.get("APP_PASSWORD"):
            session["logged_in"] = True
            return redirect(url_for("home"))
        return render_template("login.html", error="Incorrect password")
    return render_template("login.html")


@app.route("/logout")
def logout():
    """Clear session and redirect to login."""
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def home():
    return render_template("index.html")

@app.route("/files", methods=["GET"])
@login_required
def list_files():
    """List all .md files in prompts and instructions directories."""
    resources = [f.name for f in get_resource_files()]
    instructions = [f.name for f in get_instructions()]
    return jsonify({"resources": resources, "instructions": instructions})

@app.route("/upload", methods=["POST"])
@login_required
def upload_file():
    """Upload a .md file to prompts or instructions directory."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not file.filename.endswith(".md"):
        return jsonify({"error": "Only .md files are allowed"}), 400

    # Check if uploading to instructions folder
    folder = request.form.get("folder", "resources")
    target_dir = INSTRUCTIONS_DIR if folder == "instructions" else PROMPTS_DIR

    filename = secure_filename(file.filename)
    file_path = target_dir / filename
    file.save(file_path)

    return jsonify({"success": True, "filename": filename, "folder": folder})

@app.route("/delete/<folder>/<filename>", methods=["DELETE"])
@login_required
def delete_file(folder, filename):
    """Delete a .md file from prompts or instructions directory."""
    filename = secure_filename(filename)
    target_dir = INSTRUCTIONS_DIR if folder == "instructions" else PROMPTS_DIR
    file_path = target_dir / filename

    if not file_path.exists():
        return jsonify({"error": "File not found"}), 404

    file_path.unlink()
    return jsonify({"success": True})

@app.route("/chat/stream", methods=["POST"])
@login_required
def chat_stream():
    """Streaming chat endpoint using Server-Sent Events."""
    if not check_rate_limit():
        return jsonify({"error": "Rate limit exceeded. Please wait a moment."}), 429

    data = request.json
    messages = data.get("messages", [])
    model_key = data.get("model", DEFAULT_MODEL)
    model = MODELS.get(model_key, MODELS[DEFAULT_MODEL])

    if not messages:
        return jsonify({"error": "No messages provided"}), 400

    # Both tools available
    tools = [WEB_SEARCH_TOOL, READ_RESOURCE_TOOL]

    def generate():
        try:
            system_prompt = build_system_prompt()
            tool_uses = []
            current_messages = messages.copy()

            # Handle potential tool use loop (non-streaming for tool calls)
            while True:
                # Check if we need to do tool use first (non-streaming)
                initial_response = client.messages.create(
                    model=model,
                    max_tokens=MAX_TOKENS,
                    system=system_prompt,
                    messages=current_messages,
                    tools=tools
                )

                if initial_response.stop_reason != "tool_use":
                    break

                # Handle ALL tool use blocks in this turn
                tool_results = []
                for block in initial_response.content:
                    if block.type != "tool_use":
                        continue

                    tool_name = block.name
                    tool_result = ""

                    if tool_name == "web_search":
                        search_query = block.input.get("query", "")
                        tool_uses.append({"type": "search", "query": search_query})
                        yield f"data: {json.dumps({'type': 'search', 'query': search_query})}\n\n"
                        tool_result = perform_web_search(search_query)

                    elif tool_name == "read_resource":
                        filename = block.input.get("filename", "")
                        tool_uses.append({"type": "resource", "filename": filename})
                        yield f"data: {json.dumps({'type': 'resource', 'filename': filename})}\n\n"
                        tool_result = read_resource_file(filename)

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": tool_result
                    })

                if not tool_results:
                    break

                current_messages = current_messages + [
                    {"role": "assistant", "content": initial_response.content},
                    {"role": "user", "content": tool_results}
                ]

            # Now stream the final response
            with client.messages.stream(
                model=model,
                max_tokens=MAX_TOKENS,
                system=system_prompt,
                messages=current_messages,
                tools=tools
            ) as stream:
                full_text = ""
                for text in stream.text_stream:
                    full_text += text
                    yield f"data: {json.dumps({'type': 'text', 'content': text})}\n\n"

            # Send completion event
            yield f"data: {json.dumps({'type': 'done', 'tool_uses': tool_uses})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true", host="0.0.0.0", port=port)
