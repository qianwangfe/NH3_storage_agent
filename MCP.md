# MCP.md

## Codex MCP configuration

Create or edit:

```bat
notepad %USERPROFILE%\.codex\config.toml
```

Example for the current Windows layout:

```toml
[mcp_servers.hydride]
command = "D:\\Data\\tohoku_post\\AI+\\NH3\\Agent\\.venv\\Scripts\\python.exe"
args = ["D:\\Data\\tohoku_post\\AI+\\NH3\\Agent\\Hydride_NH3_Agent_Complete_Private\\hydride_nh3_agent_complete\\hydride_agent\\mcp_server.py"]
env = {
  PYTHONPATH = "D:\\Data\\tohoku_post\\AI+\\NH3\\Agent\\Hydride_NH3_Agent_Complete_Private\\hydride_nh3_agent_complete",
  HYDRIDE_API_URL = "http://127.0.0.1:8520"
}
```

Then start the backend API:

```bat
cd /d "D:\Data\tohoku_post\AI+\NH3\Agent\Hydride_NH3_Agent_Complete_Private\hydride_nh3_agent_complete"
"D:\Data\tohoku_post\AI+\NH3\Agent\.venv\Scripts\python.exe" -m uvicorn hydride_agent.api:app --host 127.0.0.1 --port 8520 --reload
```

Restart VS Code/Codex and test:

```text
List available MCP tools. Do not inspect source code.
```

Expected Hydride tools:

- `mcp__hydride.list_databases`
- `mcp__hydride.list_skills`
- `mcp__hydride.run_skill`
- `mcp__hydride.answer_question`
- `mcp__hydride.state_sequence_lookup`
- `mcp__hydride.state_complexity`
