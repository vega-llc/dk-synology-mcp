# Synology MCP Server

Comprehensive Synology NAS management through the [Model Context Protocol](https://modelcontextprotocol.io/). Control file operations, downloads, backups, Docker containers, photos, virtual machines, snapshots, and more — all from Claude or any MCP-compatible client.

## Features

- **87 tools** across 15 service categories
- **Multi-NAS support** — manage up to 9 NAS units from a single server
- **DSM 7 and DSM 6** compatibility
- **Secure connections** — HTTPS with optional certificate verification
- **Two-factor auth** — OTP code support per NAS

### Tool Categories

| Category | Tools | Description |
|----------|-------|-------------|
| File Management | 16 | List, search, create folders, copy/move, delete, compress, share links, file tree |
| System Info | 6 | DSM info, CPU/RAM utilization, storage, network, services, health dashboard |
| Download Station | 8 | Create downloads (URL/magnet), pause/resume, delete, stats, config |
| Cloud Sync | 5 | List sync tasks, status, pause/resume, logs |
| Backup (HyperBackup) | 5 | List tasks, status, run, cancel, integrity check |
| Docker | 8 | List containers/images/networks, start/stop/restart, logs, resource usage |
| Task Scheduler | 5 | List scheduled tasks, info, run, enable/disable, output |
| Photos | 4 | List albums, browse, search, album items |
| Packages | 4 | List installed packages, start/stop, package info |
| Users & Groups | 4 | List users/groups, user info, group members |
| Shared Folders | 3 | List shares, folder info, permissions |
| Virtualization (VMM) | 5 | List VMs, info, power on/off, graceful shutdown |
| Snapshots | 4 | List snapshots, create, delete, replication tasks |
| Active Backup | 6 | List tasks (with problem/stale filters), task and device info, logs, restore points |
| System | 4 | List connections, test connectivity, disconnect, capabilities |

## Installation

### Prerequisites

- Python 3.10+
- One or more Synology NAS units with DSM 6.x or 7.x
- An admin (or delegated) account on each NAS

### Install from source (recommended)

macOS with Homebrew Python requires a virtual environment:

```bash
git clone https://github.com/DRVBSS/dk-synology-mcp.git
cd dk-synology-mcp
python3 -m venv .venv
source .venv/bin/activate
pip install .
```

The `.venv` folder is already in `.gitignore` and won't be committed.

### Install in development mode

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Verify installation

```bash
# With venv activated:
synology-mcp --help

# Or without activating:
.venv/bin/synology-mcp --help
```

## Configuration

### Step 1: Find your Synology NAS connection details

Before configuring the server, gather these details from each NAS:

1. **Host/IP**: Your NAS IP address (e.g., `192.168.1.100`). Find it in DSM under Control Panel > Network > Network Interface.
2. **Port**: Default is `5000` (HTTP) or `5001` (HTTPS). Find it in Control Panel > Login Portal > DSM tab.
3. **Username/Password**: An admin account, or a user with delegated admin permissions. For security, consider creating a dedicated service account:
   - Go to Control Panel > User & Group > Create
   - Name it something like `mcp-service`
   - Add it to the `administrators` group (required for most API access)
   - Give it a strong password
4. **HTTPS**: Set `SECURE=true` and `PORT=5001` for HTTPS (recommended). Set `CERT_VERIFY=false` if using a self-signed certificate (common on home NAS).
5. **DSM Version**: Use `7` for DSM 7.x or `6` for DSM 6.x. Check in Control Panel > Info Center.

### Step 2: Create your .env file

```bash
cp .env.example .env
```

Edit `.env` with your NAS details:

#### Single NAS setup

```env
# === Your NAS ===
SYNOLOGY_NAS1_NAME=ds923
SYNOLOGY_NAS1_HOST=192.168.1.100
SYNOLOGY_NAS1_PORT=5001
SYNOLOGY_NAS1_USERNAME=mcp-service
SYNOLOGY_NAS1_PASSWORD=your-strong-password
SYNOLOGY_NAS1_SECURE=true
SYNOLOGY_NAS1_CERT_VERIFY=false
SYNOLOGY_NAS1_DSM_VERSION=7
SYNOLOGY_NAS1_OTP_CODE=

# === Server Settings ===
SYNOLOGY_DEFAULT_NAS=ds923
SYNOLOGY_LOG_LEVEL=INFO
```

#### Multi-NAS setup

Add additional NAS units with incrementing numbers (up to 9):

```env
# === Primary NAS ===
SYNOLOGY_NAS1_NAME=ds923
SYNOLOGY_NAS1_HOST=192.168.1.100
SYNOLOGY_NAS1_PORT=5001
SYNOLOGY_NAS1_USERNAME=mcp-service
SYNOLOGY_NAS1_PASSWORD=password-for-ds923
SYNOLOGY_NAS1_SECURE=true
SYNOLOGY_NAS1_CERT_VERIFY=false
SYNOLOGY_NAS1_DSM_VERSION=7

# === Secondary NAS ===
SYNOLOGY_NAS2_NAME=ds517
SYNOLOGY_NAS2_HOST=192.168.1.101
SYNOLOGY_NAS2_PORT=5001
SYNOLOGY_NAS2_USERNAME=mcp-service
SYNOLOGY_NAS2_PASSWORD=password-for-ds517
SYNOLOGY_NAS2_SECURE=true
SYNOLOGY_NAS2_CERT_VERIFY=false
SYNOLOGY_NAS2_DSM_VERSION=7

# === Server Settings ===
SYNOLOGY_DEFAULT_NAS=ds923
SYNOLOGY_LOG_LEVEL=INFO
```

#### Two-Factor Authentication

If a NAS has 2FA enabled, provide the current OTP code:

```env
SYNOLOGY_NAS1_OTP_CODE=123456
```

Note: OTP codes expire quickly. For persistent MCP use, create a dedicated service account without 2FA.

### Step 3: Test the connection

```bash
source .venv/bin/activate
synology-mcp
```

If it starts without errors, the server is ready. Press `Ctrl+C` to stop it.

## Claude Desktop Setup

### Step 1: Locate the config file

The Claude Desktop MCP configuration file is located at:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

If the file doesn't exist yet, create it.

### Step 2: Add the Synology MCP server

Open the config file and add (or merge into) the `mcpServers` section. You must use the **full absolute path** to the `synology-mcp` binary inside your venv:

```json
{
  "mcpServers": {
    "synology": {
      "command": "/full/path/to/dk-synology-mcp/.venv/bin/synology-mcp",
      "env": {
        "SYNOLOGY_NAS1_NAME": "ds923",
        "SYNOLOGY_NAS1_HOST": "192.168.1.100",
        "SYNOLOGY_NAS1_PORT": "5001",
        "SYNOLOGY_NAS1_USERNAME": "mcp-service",
        "SYNOLOGY_NAS1_PASSWORD": "your-password",
        "SYNOLOGY_NAS1_SECURE": "true",
        "SYNOLOGY_NAS1_CERT_VERIFY": "false",
        "SYNOLOGY_NAS1_DSM_VERSION": "7",
        "SYNOLOGY_DEFAULT_NAS": "ds923"
      }
    }
  }
}
```

For multi-NAS, add the second NAS variables in the same `env` block:

```json
{
  "mcpServers": {
    "synology": {
      "command": "/full/path/to/dk-synology-mcp/.venv/bin/synology-mcp",
      "env": {
        "SYNOLOGY_NAS1_NAME": "ds923",
        "SYNOLOGY_NAS1_HOST": "192.168.1.100",
        "SYNOLOGY_NAS1_PORT": "5001",
        "SYNOLOGY_NAS1_USERNAME": "mcp-service",
        "SYNOLOGY_NAS1_PASSWORD": "password-for-ds923",
        "SYNOLOGY_NAS1_SECURE": "true",
        "SYNOLOGY_NAS1_CERT_VERIFY": "false",
        "SYNOLOGY_NAS1_DSM_VERSION": "7",
        "SYNOLOGY_NAS2_NAME": "ds517",
        "SYNOLOGY_NAS2_HOST": "192.168.1.101",
        "SYNOLOGY_NAS2_PORT": "5001",
        "SYNOLOGY_NAS2_USERNAME": "mcp-service",
        "SYNOLOGY_NAS2_PASSWORD": "password-for-ds517",
        "SYNOLOGY_NAS2_SECURE": "true",
        "SYNOLOGY_NAS2_CERT_VERIFY": "false",
        "SYNOLOGY_NAS2_DSM_VERSION": "7",
        "SYNOLOGY_DEFAULT_NAS": "ds923"
      }
    }
  }
}
```

**Important notes:**

- Replace `/full/path/to/dk-synology-mcp` with the actual path where you cloned the repo.
- If you already have other MCP servers configured, merge the `"synology"` entry into your existing `mcpServers` object — don't replace the whole file.
- Use the full path to the venv binary (`.venv/bin/synology-mcp`), not just `synology-mcp`, because Claude Desktop doesn't activate your shell profile or venv.

### Step 3: Restart Claude Desktop

Quit Claude Desktop completely and reopen it. The Synology MCP server will appear in the MCP tools list (look for the hammer icon at the bottom of the chat input).

### Step 4: Verify it works

Try asking Claude:

- "Test my Synology NAS connection"
- "Show my NAS health dashboard"
- "List files in /volume1/homes"
- "What Docker containers are running on my NAS?"

## Usage with Docker

### Build and run (stdio transport)

```bash
docker compose up -d
```

### Build and run manually

```bash
docker build -t synology-mcp .
docker run --env-file .env -i synology-mcp
```

### SSE transport (network-accessible)

Uncomment the relevant lines in `docker-compose.yml`, or run:

```bash
docker run --env-file .env -p 8080:8080 synology-mcp --transport sse --port 8080
```

## Multi-NAS Usage

Every tool accepts an optional `nas` parameter. If omitted, the default NAS is used.

```
"List files on ds923"        → nas parameter not needed (it's the default)
"List files on ds517"        → nas="ds517"
"Show VMs on ds923"          → nas parameter not needed
"Docker containers on ds517" → nas="ds517"
```

Use `synology_list_connections` to see all configured NAS units and their active sessions, or `synology_test_connection` to verify connectivity.

## Project Structure

```
dk-synology-mcp/
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── README.md
└── src/
    └── synology_mcp/
        ├── __init__.py
        ├── server.py              # FastMCP server entry point
        ├── utils/
        │   ├── config.py          # Environment config loader
        │   ├── connection.py       # Multi-NAS ConnectionManager
        │   └── formatters.py       # Response formatting helpers
        └── tools/
            ├── filestation.py      # File management (16 tools)
            ├── sysinfo.py          # System monitoring (6 tools)
            ├── downloadstation.py  # Downloads (8 tools)
            ├── cloudsync.py        # Cloud Sync (5 tools)
            ├── backup.py           # HyperBackup (5 tools)
            ├── docker_tools.py     # Docker/Container (8 tools)
            ├── task_scheduler.py   # Scheduled tasks (5 tools)
            ├── photos.py           # Synology Photos (4 tools)
            ├── package.py          # Package management (4 tools)
            ├── users_groups.py     # Users & groups (4 tools)
            ├── shares.py           # Shared folders (3 tools)
            ├── virtualization.py   # VMM (5 tools)
            ├── snapshot.py         # Snapshots (4 tools)
            ├── active_backup.py    # Active Backup (6 tools)
            └── system_tools.py     # NAS connections (4 tools)
```

## Troubleshooting

### "command not found: synology-mcp"

You're not using the venv. Either activate it first (`source .venv/bin/activate`) or use the full path: `.venv/bin/synology-mcp`.

### "Connection refused" or timeout errors

- Verify your NAS IP is reachable: `ping 192.168.1.100`
- Verify the port is open: `curl -k https://192.168.1.100:5001`
- Check that DSM's HTTP/HTTPS service is enabled in Control Panel > Login Portal
- If using HTTPS with a self-signed cert, make sure `CERT_VERIFY=false`

### "Permission denied" or "Invalid credentials"

- Double-check the username and password in your `.env` or Claude Desktop config
- Ensure the user account is in the `administrators` group
- If 2FA is enabled on the account, either provide `OTP_CODE` or use a service account without 2FA

### Claude Desktop doesn't show Synology tools

- Make sure the `command` path in `claude_desktop_config.json` is the **full absolute path** to `.venv/bin/synology-mcp`
- Quit and fully restart Claude Desktop (not just close the window)
- Check Claude Desktop logs: `~/Library/Logs/Claude/` (macOS)

## Dependencies

- [mcp](https://pypi.org/project/mcp/) — Model Context Protocol SDK with FastMCP
- [synology-api](https://pypi.org/project/synology-api/) — Python wrapper for Synology DSM APIs
- [pydantic](https://docs.pydantic.dev/) — Input validation
- [python-dotenv](https://pypi.org/project/python-dotenv/) — Environment variable loading
- [treelib](https://pypi.org/project/treelib/) — Tree data structure for file tree visualization

### SSL hostname mismatch errors

If you get SSL errors when connecting via HTTPS, use your NAS hostname (e.g., `mynas.synology.me`) instead of a raw IP address in `SYNOLOGY_NAS1_HOST`. Self-signed certificates generated by DSM are bound to the hostname, not the IP.

## Changelog

### v0.3.0 — Runtime bug fixes and robustness (2026-03-02)

Fixed bugs discovered during real-world NAS management sessions. Every tool was exercised against a live DS923+ running DSM 7, revealing issues that only surface at runtime.

**Task handling — `_extract_taskid()` helper (`filestation.py`):**

synology-api's task-start methods (`start_delete`, `start_copy_move`, `start_compress`, `start_extract`) return a plain string like `"You can now check the status of request with get_delete_status() , task id is: FileStation_xxx"` when `interactive_output=True` (the default). The previous code expected a dict with a `"taskid"` key, causing all four operations to fail. Added `_extract_taskid()` with regex parsing to handle both response formats. Applied to all task handlers: delete, copy/move, compress, extract.

**Shared folders — `SYNO.Core.Share` KeyError (`shares.py`):**

`Share.list_folders()` in synology-api fails with `KeyError('SYNO.Core.Share')` because the API isn't enumerated in the session's `core_list` on DSM 7. All three share tools (`synology_shared_folders`, `synology_shared_folder_info`, `synology_shared_folder_permissions`) now fall back to direct `request_data()` calls with hardcoded API paths when the KeyError occurs.

**Other fixes:**

- `system_tools.py` — `synology_list_connections` and `synology_server_capabilities` iterated over dict keys instead of values (`config.nas_configs` → `config.nas_configs.values()`)
- `filestation.py` — `synology_file_tree` now uses `treelib.Tree` with `tree.show(stdout=False)` for proper ASCII tree output; added `treelib>=1.6.0` as a project dependency
- `filestation.py` — `synology_compress` used `format` parameter (Python built-in shadow) instead of the correct `compress_format`
- Claude Desktop config examples now use generic paths instead of hardcoded user paths

### v0.2.0 — API method name audit (2026-03-02)

Fixed all synology-api method calls across 13 tool files. The `synology-api` Python package uses non-obvious method names that differ from the DSM API naming conventions. Every tool now uses the correct underlying method, verified by introspection against `synology-api` v0.8.2.

**Files changed (46 method calls fixed):**

- `system_tools.py` — `get_info()` to `get_system_info()`
- `sysinfo.py` — 8 fixes: `get_dsm_info` to `dsm_info`, `get_system_utilization` to `get_all_system_utilization`, `get_storage_info` to `storage`, `get_all_service` to `services_status`
- `docker_tools.py` — 6 fixes: `get_containers` to `containers`, `restart_container` replaced with stop+start (no restart in synology-api), `get_container_log` to `get_logs`, `get_images` to `downloaded_images`, `get_networks` to `network`, `get_resources` to `container_resources`
- `cloudsync.py` — 4 fixes: `get_connection_status` to `get_connection_information`, `pause_connection` to `connection_pause`, `resume_connection` to `connection_resume`, `get_connection_log` to `get_connection_logs`
- `virtualization.py` — 5 fixes: `get_guest_list` to `get_images_list`, `get_guest_info` to `get_specific_vm_info`, `poweron_guest` to `vm_power_on`, `poweroff_guest` to `vm_force_power_off`, `shutdown_guest` to `vm_shut_down`
- `shares.py` — 3 fixes: `get_share_list` to `list_folders`, `get_share_info` to `get_folder`, `get_share_permission` to `get_folder_permissions`
- `users_groups.py` — 3 fixes: `get_list_user` to `get_users`, `get_list_group` to `get_groups`, `get_group_member` to `get_users`
- `active_backup.py` — 5 fixes: `list_task_list` to `list_tasks`, `get_task_info` to `task_history`, `list_device_list` to `list_device_transfer_size`, `get_device_info` to `list_device_transfer_size`, `list_restore_points` to `result_details`
- `package.py` — 4 fixes: `packages_installed` to `list_installed`, `package_get` to `get_package`, and package start/stop now uses direct DSM API calls via `request_data()` (synology-api has no start/stop methods)
- `photos.py` — 4 fixes: `get_albums` to `list_albums`, `get_items` to `list_item_in_folders`, `search` to `list_search_filters`, `get_album_items` to `get_album`
- `snapshot.py` — 2 fixes: `delete_snapshot` to `delete_snapshots`, `list_replication_tasks` to `list_replication_plans`
- `task_scheduler.py` — 1 fix: `get_task_result` to `get_task_results`
- `backup.py` — 1 fix: `backup_task_result` to `integrity_check_run`

**Other fixes:**

- Fixed ConnectionManager proxy pattern with module-level `_active_conn_mgr` variable
- Fixed SSL hostname mismatch by using NAS hostname instead of IP address

## License

MIT
