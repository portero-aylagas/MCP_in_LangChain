# LangChain v1 MCP Lab

This project demonstrates how to connect a LangChain v1 agent to MCP servers. The agent uses two MCP servers and can optionally create a Trello demo card with the official Trello REST API. Trello is a third-party external app integration for this lab, so use it at your own discretion:

- `filesystem`: reads and lists files from the local `documents/` folder
- `git`: inspects this lab repository by default, or another Git repository if configured in `.env`
- `trello REST API`: optionally creates or reuses a demo list, then creates a real demo card when Trello credentials and a board are configured

The lab follows the current LangChain v1 style with `create_agent` and `MultiServerMCPClient.get_tools()`.

## What This Lab Proves

This project satisfies the main lab goals:

1. Connect to MCP servers from Python.
2. Load MCP tools into LangChain.
3. Create a LangChain v1 agent.
4. Use filesystem MCP tools to inspect and read local documents.
5. Use Git MCP tools to inspect repository status.
6. Optionally use the official Trello REST API to create or reuse a list and create one real Trello card.
7. Check MCP resources and explain when none are exposed by the selected servers.

## Files

- `mcp_langchain.py`: main Python script for the MCP-enabled LangChain agent
- `documents/sample_notes.txt`: sample document used by the filesystem MCP server
- `requirements.txt`: Python dependencies
- `lab_summary.md`: short MCP vs direct API comparison
- `demo_output.txt`: optional file where terminal output can be saved after running the script
- `Lab_source/`: original saved lab instructions

## How It Works

The script creates one `MultiServerMCPClient` with two MCP server configurations:

- The filesystem server is started with `npx -y @modelcontextprotocol/server-filesystem documents/`.
- The Git server is started with `python -m mcp_server_git --repository <repo_path>`.

After the MCP servers start, LangChain loads their tools with:

```python
tools = await client.get_tools()
```

Those tools are passed into a LangChain v1 agent:

```python
agent = create_agent(model_name, tools, system_prompt=...)
```

The agent can then decide when to call filesystem or Git tools to answer user questions.

If Trello credentials are configured, the script separately calls the official Trello REST API after the MCP agent demo. This avoids running a third-party Trello MCP package while still proving external API write capability.

No Trello MCP server is used in this implementation. A third-party package, `@delorenj/mcp-server-trello`, was considered during development, but it is not part of the final code because Trello does not currently provide an official Trello-specific MCP server. The final Trello path uses official Atlassian/Trello REST API endpoints:

- `GET /1/boards/{board_id}/lists`
- `POST /1/lists`
- `POST /1/cards`

## Setup

Use Python 3.10 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The filesystem MCP server runs through `npx`, so Node.js must also be installed.

Create a `.env` file with your OpenAI API key:

```bash
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=openai:gpt-4o-mini
```

`MCP_GIT_REPOSITORY` is optional. If it is not set, the script dynamically uses this lab folder as the Git repository. The script intentionally fails fast if neither this lab folder nor the configured path is a valid Git repository, because the Git MCP server cannot start without a real repository.

If this lab folder is not already a Git repository, initialize it:

```bash
git init
git add .
git commit -m "Initial MCP LangChain lab"
```

Then set:

```bash
MCP_GIT_REPOSITORY=/absolute/path/to/another/git/repository
```

If Git says your name or email is missing:

```bash
git config user.name "Your Name"
git config user.email "you@example.com"
```

## Optional Trello API Setup

Trello is disabled unless the API key, token, and board ID are present in `.env`. This keeps the filesystem and Git lab demos runnable without Trello.

Trello is a third-party app outside this lab and outside the MCP servers used here. Enabling this demo gives the script a write-capable Trello token, so use it at your own discretion. Recommended practice:

- use an empty test board only
- create a token only for this lab
- do not use company, client, or personal production boards
- revoke the token after the demo
- keep `.env` out of git
- prefer the optional `TRELLO_LIST_ID` only when you intentionally want to write to a known existing list

```bash
TRELLO_API_KEY=your_trello_api_key_here
TRELLO_TOKEN=your_trello_token_here
TRELLO_BOARD_ID=your_trello_board_id_here
```

When these values are set, the script uses the official Trello REST API to create one real card. Trello cards must live inside lists, so the script first creates or reuses a demo list on the configured board:

```bash
TRELLO_LIST_NAME=MCP Demo
```

`TRELLO_LIST_NAME` is optional and defaults to `MCP Demo`. If you already have a specific target list, you can bypass dynamic list creation:

```bash
TRELLO_LIST_ID=your_trello_list_id_here
```

The write demo creates:

- list: `TRELLO_LIST_NAME` when `TRELLO_LIST_ID` is not set
- name: `MCP LangChain demo card`
- description: `Created by the MCP in LangChain lab to demonstrate Trello API write capability.`
- target list: `TRELLO_LIST_ID`, or the dynamically created/reused demo list

Get a Trello API key from https://trello.com/app-key. Generate a token from that API key with read/write scope, for example by visiting:

```text
https://trello.com/1/authorize?expiration=never&name=MCP%20LangChain%20Lab&scope=read,write&response_type=token&key=YOUR_API_KEY
```

Replace `YOUR_API_KEY` with your actual key. Use the board ID from the Trello board URL. Keep these values in `.env`; the script reports missing Trello variable names, but never prints Trello secret values.

## Run

```bash
python mcp_langchain.py
```

To save proof of the run:

```bash
python mcp_langchain.py > demo_output.txt
```

## Expected Output

When the script works, you should see:

- a message saying the Trello API demo was skipped, or a message saying it is configured
- a connection message for the filesystem and Git MCP servers
- a list of loaded tools, including names like `filesystem_list_directory` and `git_git_status`
- an answer listing files in `documents/`
- an answer summarizing `sample_notes.txt`
- an answer describing the Git repository status
- when Trello is configured, output confirming the real Trello list/card creation

Note: the configured MCP servers mainly expose tools. The script also calls `get_resources()` and prints any resources exposed by the configured servers. If no resources appear, that is a property of these servers, not a LangChain error.

## Troubleshooting

### `OPENAI_API_KEY is not set`

Create a `.env` file or export the key in your terminal:

```bash
export OPENAI_API_KEY=your_openai_api_key_here
```

### `model_not_found` or `does not have access to model`

Your OpenAI project does not have access to the configured model. This project defaults to:

```bash
OPENAI_MODEL=openai:gpt-4o-mini
```

Use another model only if your OpenAI project has access to it.

### `No Git repository is configured`

The Git MCP server requires a real Git repository. Run:

```bash
git init
git add .
git commit -m "Initial MCP LangChain lab"
```

### `Client does not support MCP Roots`

This is an informational message from the filesystem MCP server. The script passes the allowed directory directly as a server argument, so this message is expected and not an error.

### `Could not load resources from these servers`

The selected filesystem and Git MCP servers mainly expose tools. This message does not stop the tool-based demo from working.

### `Trello API demo skipped`

This is expected unless you want to run the optional Trello write demo. Set `TRELLO_API_KEY`, `TRELLO_TOKEN`, and `TRELLO_BOARD_ID` in `.env` to enable it. `TRELLO_LIST_ID` is optional.

## References

- LangChain Python MCP docs: https://docs.langchain.com/oss/python/langchain/mcp
- LangChain MCP adapters reference: https://reference.langchain.com/python/langchain-mcp-adapters/client/MultiServerMCPClient
- MCP reference servers: https://github.com/modelcontextprotocol/servers
- Third-party Trello MCP package considered but not used: https://github.com/delorenj/mcp-server-trello
- Trello REST API introduction: https://developer.atlassian.com/cloud/trello/guides/rest-api/api-introduction/
- Trello lists API: https://developer.atlassian.com/cloud/trello/rest/api-group-lists/
- Trello cards API: https://developer.atlassian.com/cloud/trello/rest/api-group-cards/
