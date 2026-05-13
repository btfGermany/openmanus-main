# OpenManus API Service - Analysis Document

## 1. Current OpenManus Architecture Overview

### 1.1 Agent Entry Points

| Entry Point | File | Description |
|-----------|------|-----------|
| Direct Agent | `main.py` | Standalone async execution of Manus agent |
| Flow Mode | `run_flow.py` | Flow-based execution with Planning flow |
| MCP Server | `run_mcp.py`, `run_mcp_server.py` | MCP protocol servers |

### 1.2 Core Agent Hierarchy

```
BaseAgent (base.py)
    │
    ├── ReActAgent (react.py)
    │       │── think(): bool (decide next action)
    │       │── act(): str (execute action)
    │       └── step(): str (think + act loop)
    │
    └── ToolCallAgent (toolcall.py)
            │── execute_tool(command): str
            │── think(): bool (LLM + tool selection)
            │── act(): str (execute all tool calls)
            │── run(): str (main loop with max_steps)
            │── cleanup()
            │
            └── Manus (manus.py)
                    │── + MCP server integration
                    │── + Browser context helper
                    │── + General-purpose tools
                    └── create() factory method
```

### 1.3 Agent Execution Flow

```
Manus.create()
    │
    ├── initialize_mcp_servers()
    │
    └── run(prompt):
            │
            ├── BaseAgent.run():
            │       │
            │       └── while current_step < max_steps and state != FINISHED:
            │               │
            │               ├── step() → think() → act()
            │               ├── execute_tool() for each tool
            │               ├── capture tool results
            │               ├── check stuck state
            │               │
            │               └── on max_steps or FINISHED → cleanup() → return results
            │
            └── cleanup():
                    ├── browser_context_helper.cleanup_browser()
                    └── disconnect_mcp_server()
```

### 1.4 Configuration System

**Config Loading Order:**
1. `config/config.toml` → `config/config/example.toml` → raises FileNotFoundError
2. Pydantic models: `LLMSettings`, `BrowserSettings`, `SandboxSettings`, `MCPSettings`
3. Loaded via singleton `app.config.Config`

**Key Config Properties:**
```python
config.llm                 # Dict[str, LLMSettings]
config.sandbox              # SandboxSettings
config.browser_config       # Optional[BrowserSettings]
config.search_config       # Optional[SearchSettings]
config.mcp_config        # MCPSettings
config.workspace_root    # Path to workspace directory
config.root_path        # Path to project root
```

### 1.5 LLM Integration

**Location:** `app/llm.py`

**Key Features:**
- Singleton pattern per `config_name`: `LLM(config_name="default")`
- Supports: OpenAI, Azure OpenAI, AWS Bedrock, Ollama
- Token counting with tiktoken
- Tool calling via `ask_tool()`
- Retry with tenacity for resilience

**Token Limit Handling:**
- Custom `TokenLimitExceeded` exception
- Max input tokens configurable per LLM config

### 1.6 Tool System

**Built-in Tools:**
- `PythonExecute()` - Execute Python code
- `BrowserUseTool()` - Browser automation
- `StrReplaceEditor()` - File editing
- `AskHuman()` - Human-in-the-loop
- `Terminate()` - Signal completion
- MCP tools via `MCPClients`

**Tool Execution:**
```python
available_tools.execute(name=tool_name, tool_input=args)
```

### 1.7 Logging

**Location:** `app/logger.py`

- Uses `loguru` library
- Log levels: DEBUG, INFO, WARNING, ERROR
- Output: stderr + `logs/{date}.log`
- Configurable via `define_log_level()`

---

## 2. Integration Boundaries for API Layer

### 2.1 What the API Must Wrap

| Component | Wrap Method | Notes |
|----------|-----------|-------|
| Agent Creation | `Manus.create()` | Async factory method |
| Agent Execution | `agent.run(prompt)` | Async, returns string |
| Agent Cleanup | `await agent.cleanup()` | Must be called on completion/timeout |
| Workspace | `config.workspace_root` | Create task-specific subdirectories |
| Config | `config.llm` | For per-request LLM overrides |

### 2.2 What Must Be Captured/Emulated

| Output Type | Capture Method | Target |
|-----------|------------|--------|
| Agent thoughts | `logger.info()` / `super().think()` | Stream as `iteration_start` events |
| Tool calls | `execute_tool()` instrumentation | Stream as `tool_call` events |
| Tool results | Tool execution return values | Stream as `tool_result` events |
| Stdout/Stderr | Tool output capture | Stream as `observation` events |
| Final results | `run()` return value | Stream as `final_result` event |
| Errors | Exception handling | Stream as `error` events |

### 2.3 Event Mapping to SSE Types

| Agent Stage | SSE Event | Data |
|-----------|----------|------|
| Plan creation | `plan_created` | Steps from Flow (if flow mode) |
| Iteration start | `iteration_start` | iteration, thought |
| Tool call | `tool_call` | tool name, input |
| Tool result | `tool_result` | tool, output, duration_ms |
| Execution output | `observation` | stdout, stderr, exit_code |
| Plan update | `plan_update` | step_id, status |
| Error | `error` | error_class, message, recoverable |
| Final result | `final_result` | final_answer, output_files |
| Done | `done` | status, total_duration_ms |

### 2.4 Configuration Overrides

The API should support per-request config overrides:
```python
class TaskCreateRequest:
    goal: str
    mode: Literal["direct", "flow", "research"] = "flow"
    timeout_seconds: int = 300
    max_iterations: int = 20
    llm_model: Optional[str] = None  # Override config.llm
```

---

## 3. Migration Strategy

### 3.1 Files to Create (New API Layer)

| Path | Purpose |
|------|--------|
| `/api/` | FastAPI application root |
| `/api/main.py` | FastAPI entry point |
| `/api/routes/tasks.py` | Task endpoints |
| `/api/routes/health.py` | Health check |
| `/api/routes/admin.py` | Admin API key management |
| `/api/models.py` | Pydantic request/response models |
| `/api/auth.py` | API key validation middleware |
| `/api/rate_limiter.py` | Redis-backed rate limiting |
| `/worker/` | RQ worker for background tasks |
| `/worker/worker.py` | Worker implementation |
| `/workspace/tasks/{task_id}/` | Per-task workspace |
| `/docker-compose.yml` | Docker deployment |
| `/api/config.toml` | API-specific config |

### 3.2 Files to Modify (Minimal Changes)

| File | Modification |
|------|------------|
| None required | Wrap via imports, don't modify |

### 3.3 Files to Preserve (Untouched)

- All `app/agent/*.py`
- All `app/tool/*.py`
- All `app/flow/*.py`
- `main.py`, `run_flow.py`, etc.
- `config/config.toml`
- `app/config.py`

---

## 4. Workspace Structure for API

```
/workspace/                          # ROOT from docker-compose
├── tasks/                        # API task workspaces
│   └── {task_id}/
│       ├── data/               # Intermediate data
│       ├── reports/            # Output reports
│       ├── logs/              # Task-specific JSONL logs
│       ├── notes/             # Agent scratchpad
│       └── sandbox/          # Mounted for Docker sandbox
├── api_logs/                   # API service logs
│   ├── api_requests.jsonl
│   ├── tasks.jsonl
│   ├── llm_calls.jsonl
│   ├── sandbox_exec.jsonl
│   └── errors.jsonl
└── data/                     # SQLite DBs for API keys, etc.
    └── api_keys.db
```

---

## 5. Key Implementation Notes

### 5.1 Async Agent Invocation

The Manus agent is fully async:
```python
agent = await Manus.create()
try:
    result = await agent.run(prompt)
finally:
    await agent.cleanup()
```

### 5.2 Event Streaming Strategy

Since OpenManus uses `loguru` for logging, the worker should:
1. Monkey-patch or wrap the logger to intercept key events
2. Subscribe to Redis Pub/Sub for cross-process streaming
3. Emit SSE events directly from tool execution hooks

### 5.3 Sandbox Isolation

Two options for task isolation:
1. **Docker-per-task**: Spawn a new container per task via Docker SDK
2. **Directory-per-task**: Use filesystem isolation (simpler, recommended for initial implementation)

### 5.4 Timeout Enforcement

- Task-level timeout: `asyncio.wait_for(agent.run(prompt), timeout=timeout_seconds)`
- Worker-level timeout: RQ job timeout setting
- Signal-based timeout: Use `signal.alarm()` for hard limits

---

## 6. Backward Compatibility

The existing OpenManus CLI continues to work:
```bash
python main.py --prompt "Your task"
python run_flow.py
```

The API layer is **additive** - it wraps the existing runtime without modification.

---

*Generated: 2026-05-13*
*For: OpenManus API Service Refactor*