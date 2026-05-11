# LangChain v1 MCP Lab

This project demonstrates how to connect a LangChain v1 agent to MCP servers. The agent uses two MCP servers:

- `filesystem`: reads and lists files from the local `documents/` folder
- `git`: inspects this lab repository by default, or another Git repository if configured in `.env`

The lab follows the current LangChain v1 style with `create_agent` and `MultiServerMCPClient.get_tools()`.

## What This Lab Proves

This project satisfies the main lab goals:

1. Connect to MCP servers from Python.
2. Load MCP tools into LangChain.
3. Create a LangChain v1 agent.
4. Use filesystem MCP tools to inspect and read local documents.
5. Use Git MCP tools to inspect repository status.
6. Check MCP resources and explain when none are exposed by the selected servers.

## Files

- `mcp_langchain.py`: main Python script for the MCP-enabled LangChain agent
- `documents/sample_notes.txt`: sample document used by the filesystem MCP server
- `requirements.txt`: Python dependencies
- `lab_summary.md`: short MCP vs direct API comparison
- `demo_output.txt`: optional file where terminal output can be saved after running the script
- `Lab_source/`: original saved lab instructions

## How It Works

The script creates one `MultiServerMCPClient` with two server configurations:

- The filesystem server is started with `npx -y @modelcontextprotocol/server-filesystem documents/`.
- The Git server is started with `python -m mcp_server_git --repository <repo_path>`.

After both servers start, LangChain loads their tools with:

```python
tools = await client.get_tools()
```

Those tools are passed into a LangChain v1 agent:

```python
agent = create_agent(model_name, tools, system_prompt=...)
```

The agent can then decide when to call filesystem or Git tools to answer user questions.

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

- a connection message for the filesystem and Git MCP servers
- a list of loaded tools, including names like `filesystem_list_directory` and `git_git_status`
- an answer listing files in `documents/`
- an answer summarizing `sample_notes.txt`
- an answer describing the Git repository status

Note: the filesystem and git reference MCP servers mainly expose tools. The script also calls `get_resources()` and prints any resources exposed by the configured servers. If no resources appear, that is a property of these two servers, not a LangChain error.

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

## References

- LangChain Python MCP docs: https://docs.langchain.com/oss/python/langchain/mcp
- LangChain MCP adapters reference: https://reference.langchain.com/python/langchain-mcp-adapters/client/MultiServerMCPClient
- MCP reference servers: https://github.com/modelcontextprotocol/servers
