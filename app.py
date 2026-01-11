"""
Peter McEwen Field Assistant
A chat interface with web search capabilities.
"""

from flask import Flask, render_template, request, jsonify, Response
from anthropic import Anthropic
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import os
import json
import requests
from pathlib import Path

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

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

# Prompts directories
PROMPTS_DIR = Path(__file__).parent / "prompts"
INSTRUCTIONS_DIR = PROMPTS_DIR / "instructions"

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

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/files", methods=["GET"])
def list_files():
    """List all .md files in prompts and instructions directories."""
    resources = [f.name for f in get_resource_files()]
    instructions = [f.name for f in get_instructions()]
    return jsonify({"resources": resources, "instructions": instructions})

@app.route("/upload", methods=["POST"])
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
def delete_file(folder, filename):
    """Delete a .md file from prompts or instructions directory."""
    filename = secure_filename(filename)
    target_dir = INSTRUCTIONS_DIR if folder == "instructions" else PROMPTS_DIR
    file_path = target_dir / filename

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


@app.route("/chat/stream", methods=["POST"])
def chat_stream():
    """Streaming chat endpoint using Server-Sent Events."""
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

                # Handle tool use
                tool_use_block = None
                for block in initial_response.content:
                    if block.type == "tool_use":
                        tool_use_block = block
                        break

                if not tool_use_block:
                    break

                # Execute the appropriate tool
                tool_name = tool_use_block.name
                tool_result = ""

                if tool_name == "web_search":
                    search_query = tool_use_block.input.get("query", "")
                    tool_uses.append({"type": "search", "query": search_query})
                    yield f"data: {json.dumps({'type': 'search', 'query': search_query})}\n\n"
                    tool_result = perform_web_search(search_query)

                elif tool_name == "read_resource":
                    filename = tool_use_block.input.get("filename", "")
                    tool_uses.append({"type": "resource", "filename": filename})
                    yield f"data: {json.dumps({'type': 'resource', 'filename': filename})}\n\n"
                    tool_result = read_resource_file(filename)

                current_messages = current_messages + [
                    {"role": "assistant", "content": initial_response.content},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_use_block.id,
                                "content": tool_result
                            }
                        ]
                    }
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
    app.run(debug=True, host="0.0.0.0", port=port)
