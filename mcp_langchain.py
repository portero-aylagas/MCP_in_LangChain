"""LangChain v1 agent using MCP servers, plus optional Trello API comparison.

This script demonstrates the main lab requirements:
- connect LangChain to MCP servers
- load MCP tools
- create a LangChain agent
- ask the agent to use filesystem, git, and optional Trello MCP capabilities
- optionally create Trello demo cards with both Trello MCP and REST API

Run:
    python mcp_langchain.py
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient


PROJECT_ROOT = Path(__file__).resolve().parent
DOCUMENTS_DIR = PROJECT_ROOT / "documents"
TRELLO_REQUIRED_ENV = (
    "TRELLO_API_KEY",
    "TRELLO_TOKEN",
    "TRELLO_BOARD_ID",
)
TRELLO_DEFAULT_LIST_NAME = "MCP Demo"
TRELLO_MCP_PACKAGE = "@delorenj/mcp-server-trello"
TRELLO_API_CARD_NAME = "MCP LangChain demo card (REST API)"
TRELLO_API_CARD_DESCRIPTION = (
    "Created by the MCP in LangChain lab to demonstrate Trello API write capability."
)
TRELLO_MCP_CARD_NAME = "MCP LangChain demo card (Trello MCP)"
TRELLO_MCP_CARD_DESCRIPTION = (
    "Created by the MCP in LangChain lab to demonstrate Trello MCP write capability."
)
TRELLO_API_BASE_URL = "https://api.trello.com/1"


@dataclass(frozen=True)
class TrelloConfig:
    """Trello settings for the optional MCP vs REST API write comparison."""

    api_key: str
    token: str
    board_id: str
    list_id: str | None
    list_name: str


def require_command(command: str, install_hint: str) -> None:
    """Fail early with a useful message when a local command is missing."""
    if shutil.which(command) is None:
        raise RuntimeError(f"Missing command: {command}. {install_hint}")


def get_trello_config() -> TrelloConfig | None:
    """Return Trello config when the required credentials and board are present."""
    values = {name: os.getenv(name) for name in TRELLO_REQUIRED_ENV}
    missing = [name for name, value in values.items() if not value]

    if missing:
        print(
            "Trello comparison demo skipped. To enable it, set all required Trello "
            f"environment variables. Missing: {', '.join(missing)}",
            flush=True,
        )
        return None

    list_id = os.getenv("TRELLO_LIST_ID") or None
    list_name = os.getenv("TRELLO_LIST_NAME") or TRELLO_DEFAULT_LIST_NAME
    if list_id:
        print("Trello comparison demo configured for the target Trello list.", flush=True)
    else:
        print(
            "Trello comparison demo configured. The script will create or reuse a "
            f"'{list_name}' list for the demo card.",
            flush=True,
        )

    return TrelloConfig(
        api_key=values["TRELLO_API_KEY"] or "",
        token=values["TRELLO_TOKEN"] or "",
        board_id=values["TRELLO_BOARD_ID"] or "",
        list_id=list_id,
        list_name=list_name,
    )


def build_mcp_client(trello_config: TrelloConfig | None = None) -> MultiServerMCPClient:
    """Configure the filesystem, git, and optional third-party Trello MCP servers.

    The filesystem server uses Node/npm through npx.
    The git server uses the Python package mcp-server-git.
    The optional Trello server uses the third-party @delorenj/mcp-server-trello
    package through npx for comparison with direct REST API calls.
    """
    git_repository = get_git_repository_path()

    # Each entry starts one MCP server. LangChain talks to these servers through
    # stdio and converts their MCP tools into normal LangChain tools.
    servers = {
        "filesystem": {
            "transport": "stdio",
            "command": "npx",
            "args": [
                "-y",
                "@modelcontextprotocol/server-filesystem",
                str(DOCUMENTS_DIR),
            ],
        },
        "git": {
            "transport": "stdio",
            "command": "python",
            "args": [
                "-m",
                "mcp_server_git",
                "--repository",
                str(git_repository),
            ],
        },
    }

    if trello_config:
        servers["trello"] = {
            "transport": "stdio",
            "command": "npx",
            "args": [
                "-y",
                TRELLO_MCP_PACKAGE,
            ],
            "env": {
                "TRELLO_API_KEY": trello_config.api_key,
                "TRELLO_TOKEN": trello_config.token,
                "TRELLO_BOARD_ID": trello_config.board_id,
            },
        }

    return MultiServerMCPClient(servers, tool_name_prefix=True)


def trello_request(
    config: TrelloConfig,
    method: str,
    path: str,
    params: dict[str, str] | None = None,
) -> dict | list:
    """Call the official Trello REST API without logging secrets."""
    request_params = {
        "key": config.api_key,
        "token": config.token,
        **(params or {}),
    }
    encoded_params = urllib.parse.urlencode(request_params).encode()
    url = f"{TRELLO_API_BASE_URL}{path}"

    if method == "GET":
        url = f"{url}?{encoded_params.decode()}"
        request_data = None
    else:
        request_data = encoded_params

    request = urllib.request.Request(
        url,
        data=request_data,
        method=method,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = response.read().decode()
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode(errors="replace")
        raise RuntimeError(
            f"Trello API request failed with HTTP {exc.code}: {error_body}"
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Trello API request failed: {exc.reason}") from exc

    if not data:
        return {}

    return json.loads(data)


def get_or_create_trello_list(config: TrelloConfig) -> dict:
    """Return the configured Trello list, creating the demo list when needed."""
    if config.list_id:
        return {"id": config.list_id, "name": "configured list"}

    board_path = f"/boards/{urllib.parse.quote(config.board_id)}/lists"
    lists = trello_request(
        config,
        "GET",
        board_path,
        {
            "cards": "none",
            "filter": "open",
            "fields": "name",
        },
    )

    if not isinstance(lists, list):
        raise RuntimeError("Trello API returned an unexpected response for board lists.")

    for trello_list in lists:
        if trello_list.get("name") == config.list_name:
            return trello_list

    created_list = trello_request(
        config,
        "POST",
        "/lists",
        {
            "name": config.list_name,
            "idBoard": config.board_id,
        },
    )

    if not isinstance(created_list, dict) or "id" not in created_list:
        raise RuntimeError("Trello API did not return a list ID after creating a list.")

    return created_list


def create_trello_api_demo_card(config: TrelloConfig, trello_list: dict) -> dict:
    """Create one real Trello card through the official Trello REST API."""
    list_id = trello_list["id"]
    list_name = trello_list.get("name", config.list_name)

    card = trello_request(
        config,
        "POST",
        "/cards",
        {
            "idList": list_id,
            "name": TRELLO_API_CARD_NAME,
            "desc": TRELLO_API_CARD_DESCRIPTION,
        },
    )

    if not isinstance(card, dict) or "id" not in card:
        raise RuntimeError("Trello API did not return a card ID after creating a card.")

    card_url = card.get("url", "(no URL returned)")
    print("\nTrello REST API demo:", flush=True)
    print(f"- Created card: {card.get('name', TRELLO_API_CARD_NAME)}", flush=True)
    print(f"- Target list: {list_name}", flush=True)
    print(f"- Card URL: {card_url}", flush=True)
    return card


async def run_trello_mcp_demo(agent, trello_list: dict) -> None:
    """Ask the agent to create one Trello card through Trello MCP tools."""
    list_id = trello_list["id"]
    question = (
        "Use the Trello MCP tools to create exactly one Trello card in this "
        f"list ID: {list_id}. Card name: {TRELLO_MCP_CARD_NAME}. "
        f"Card description: {TRELLO_MCP_CARD_DESCRIPTION}. "
        "Do not create any extra lists or cards. Mention that you used the "
        "Trello MCP server, and include the card URL or card ID if the tool "
        "returns one."
    )
    await ask_agent(agent, question)


async def run_trello_comparison_demo(agent, config: TrelloConfig) -> None:
    """Create comparable Trello cards through REST API and Trello MCP."""
    trello_list = get_or_create_trello_list(config)
    list_name = trello_list.get("name", config.list_name)

    print("\nTrello MCP vs REST API comparison:", flush=True)
    print(f"- Third-party Trello MCP package: {TRELLO_MCP_PACKAGE}", flush=True)
    print("- Direct API: official Atlassian/Trello REST API", flush=True)
    print(f"- Shared target list: {list_name}", flush=True)

    create_trello_api_demo_card(config, trello_list)
    await run_trello_mcp_demo(agent, trello_list)

    print("\nTrello comparison summary:", flush=True)
    print(f"- REST API card: {TRELLO_API_CARD_NAME}", flush=True)
    print(f"- Trello MCP card: {TRELLO_MCP_CARD_NAME}", flush=True)
    print(
        "- Both paths use the same Trello credentials and target list; the REST "
        "path is explicit Python HTTP code, while the MCP path goes through "
        "LangChain tools exposed by the third-party MCP server.",
        flush=True,
    )


def get_git_repository_path() -> Path:
    """Return the Git repository that the MCP git server should inspect."""
    git_repository = os.getenv("MCP_GIT_REPOSITORY")
    if git_repository:
        return Path(git_repository).expanduser().resolve()

    # Beginner-friendly default: use this project if it is already a Git repo.
    # This keeps the lab portable and avoids hardcoded machine-specific paths.
    result = subprocess.run(
        ["git", "-C", str(PROJECT_ROOT), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode == 0:
        return Path(result.stdout.strip()).resolve()

    raise RuntimeError(
        "No Git repository is configured.\n\n"
        "The Git MCP server needs a valid Git repository. You have two options:\n\n"
        "Option 1, initialize this lab folder as a repository:\n"
        "    git init\n"
        "    git add .\n"
        '    git commit -m "Initial MCP LangChain lab"\n\n'
        "Option 2, point the script to another existing repository in .env:\n"
        "    MCP_GIT_REPOSITORY=/absolute/path/to/your/git/repository"
    )


def validate_git_repository(repo_path: Path) -> None:
    """Check that the Git MCP server will receive a valid repository path."""
    result = subprocess.run(
        ["git", "-C", str(repo_path), "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "The Git MCP server needs a valid Git repository, but this path is "
            f"not one: {repo_path}\n\n"
            "Fix option 1, point the script to an existing repository in .env:\n"
            "    MCP_GIT_REPOSITORY=/absolute/path/to/your/git/repository"
            "\n\n"
            "Fix option 2, initialize the selected folder as a Git repository:\n"
            f"    git -C {repo_path} init\n"
            f"    git -C {repo_path} add .\n"
            f'    git -C {repo_path} commit -m "Initial commit"'
        )


def format_final_message(response: dict) -> str:
    """Extract the final assistant message from a LangChain agent response."""
    messages = response.get("messages", [])
    if not messages:
        return str(response)

    final_message = messages[-1]
    content = getattr(final_message, "content", final_message)
    return str(content)


async def ask_agent(agent, question: str) -> None:
    """Run one question through the agent and print the final answer."""
    print("\n" + "=" * 80, flush=True)
    print(f"Question: {question}", flush=True)
    print("-" * 80, flush=True)

    response = await agent.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": question,
                }
            ]
        }
    )
    print(format_final_message(response), flush=True)


async def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env")

    # The filesystem MCP server is distributed as an npm package and is started
    # with npx. Git MCP is installed through Python requirements.
    require_command("npx", "Install Node.js from https://nodejs.org/.")

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add it to a .env file or export it "
            "before running this script."
        )

    if not DOCUMENTS_DIR.exists():
        raise RuntimeError(f"Missing documents directory: {DOCUMENTS_DIR}")

    model_name = os.getenv("OPENAI_MODEL", "openai:gpt-4o-mini")
    git_repository = get_git_repository_path()
    validate_git_repository(git_repository)

    trello_config = get_trello_config()
    client = build_mcp_client(trello_config)

    configured_servers = "filesystem, git"
    if trello_config:
        configured_servers += ", trello"

    print(f"Connecting to MCP servers: {configured_servers}", flush=True)
    tools = await client.get_tools()

    # Not every MCP server exposes resources. The lab still demonstrates the
    # resource access step by checking for them and reporting the result.
    try:
        resources = await client.get_resources()
    except Exception as exc:
        resources = []
        resources_error = exc
    else:
        resources_error = None

    print("\nLoaded MCP tools:", flush=True)
    for tool in tools:
        print(f"- {tool.name}: {tool.description}", flush=True)

    print("\nLoaded MCP resources:", flush=True)
    if resources_error:
        print(f"- Could not load resources from these servers: {resources_error}", flush=True)
    elif resources:
        for resource in resources:
            source = getattr(resource, "source", "unknown source")
            print(f"- {source}", flush=True)
    else:
        print("- No resources exposed by the configured MCP servers.", flush=True)

    agent = create_agent(
        model_name,
        tools,
        system_prompt=(
            "You are a practical lab assistant. Use the available MCP tools "
            "when the user asks about files, git repository information, or Trello. "
            "Keep answers concise and mention which MCP server capability you used. "
            f"The filesystem server is limited to this directory: {DOCUMENTS_DIR}. "
            f"When using git tools, pass this repo_path value: {git_repository}. "
            "When asked to create Trello cards, use the Trello MCP tools."
        ),
    )

    questions = [
        "Use the filesystem tools to list the files available in the documents folder.",
        "Read sample_notes.txt with the filesystem tools and summarize it in 3 bullet points.",
        "Use the git tools to inspect this repository and tell me the current git status.",
    ]

    for question in questions:
        await ask_agent(agent, question)

    if trello_config:
        await run_trello_comparison_demo(agent, trello_config)


if __name__ == "__main__":
    asyncio.run(main())
