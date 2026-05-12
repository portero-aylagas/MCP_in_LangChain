"""Prompt templates for the MCP LangChain project."""

from __future__ import annotations

from pathlib import Path


AGENT_SYSTEM_PROMPT_TEMPLATE = """You are a practical lab assistant.

Use the available MCP tools when the user asks about files, git repository
information, or Trello.

Context:
- Filesystem MCP directory: {documents_dir}
- Git MCP repo_path value: {git_repository}

Rules:
- Keep answers concise.
- Mention which MCP server capability you used.
- If a tool fails, briefly report the tool error and do not claim success.
- When using git tools, pass the repo_path value shown above.
- When asked to create Trello cards, use the Trello MCP tools.
"""

LIST_DOCUMENTS_PROMPT = """Use the filesystem MCP tools to list files in the documents folder.

Return:
- One bullet per file
- File names only
- If the folder cannot be read, briefly report the tool error
"""

SUMMARIZE_DOCUMENT_PROMPT = """Use the filesystem MCP tools to read filesystem_mcp_demo.txt.

Return exactly 3 bullet points summarizing the file.
If the file cannot be read, briefly report the tool error.
"""

GIT_STATUS_PROMPT = """Use the git MCP tools to inspect this repository.

Return:
1. Current branch
2. Whether the working tree is clean
3. Modified or untracked files, if any
If Git status cannot be retrieved, briefly report the tool error.
"""


def build_agent_system_prompt(documents_dir: Path, git_repository: Path) -> str:
    """Build the agent system prompt with clearly separated runtime context."""
    return AGENT_SYSTEM_PROMPT_TEMPLATE.format(
        documents_dir=documents_dir,
        git_repository=git_repository,
    )


def build_trello_mcp_card_prompt(
    list_id: str,
    card_name: str,
    card_description: str,
) -> str:
    """Build the Trello card prompt with dynamic values separated from rules."""
    return f"""Use the Trello MCP tools to create exactly one card.

Target list ID:
{list_id}

Card name:
{card_name}

Card description:
{card_description}

Rules:
- Do not create any lists.
- Do not create extra cards.
- Mention that you used the Trello MCP server.
- Include the card URL or card ID if the tool returns one.
- If card creation fails, briefly report the tool error and do not claim success.
"""
