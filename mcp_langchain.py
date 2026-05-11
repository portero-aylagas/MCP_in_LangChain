"""LangChain v1 agent using filesystem and git MCP servers.

This script demonstrates the main lab requirements:
- connect LangChain to MCP servers
- load MCP tools
- create a LangChain agent
- ask the agent to use filesystem and git capabilities

Run:
    python mcp_langchain.py
"""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
from pathlib import Path

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient


PROJECT_ROOT = Path(__file__).resolve().parent
DOCUMENTS_DIR = PROJECT_ROOT / "documents"


def require_command(command: str, install_hint: str) -> None:
    """Fail early with a useful message when a local command is missing."""
    if shutil.which(command) is None:
        raise RuntimeError(f"Missing command: {command}. {install_hint}")


def build_mcp_client() -> MultiServerMCPClient:
    """Configure the filesystem and git MCP servers.

    The filesystem server uses Node/npm through npx.
    The git server uses the Python package mcp-server-git.
    """
    git_repository = get_git_repository_path()

    # Each entry starts one MCP server. LangChain talks to both servers through
    # stdio and converts their MCP tools into normal LangChain tools.
    return MultiServerMCPClient(
        {
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
        },
        tool_name_prefix=True,
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
    client = build_mcp_client()

    print("Connecting to MCP servers: filesystem and git", flush=True)
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
        print("- No resources exposed by the configured filesystem/git servers.", flush=True)

    agent = create_agent(
        model_name,
        tools,
        system_prompt=(
            "You are a practical lab assistant. Use the available MCP tools "
            "when the user asks about files or git repository information. "
            "Keep answers concise and mention which MCP server capability you used. "
            f"The filesystem server is limited to this directory: {DOCUMENTS_DIR}. "
            f"When using git tools, pass this repo_path value: {git_repository}."
        ),
    )

    questions = [
        "Use the filesystem tools to list the files available in the documents folder.",
        "Read sample_notes.txt with the filesystem tools and summarize it in 3 bullet points.",
        "Use the git tools to inspect this repository and tell me the current git status.",
    ]

    for question in questions:
        await ask_agent(agent, question)


if __name__ == "__main__":
    asyncio.run(main())
