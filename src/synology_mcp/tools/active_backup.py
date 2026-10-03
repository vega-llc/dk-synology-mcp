"""Active Backup for Business tools — PC, server, and VM backup monitoring.

Covers: list tasks, task details, device list, backup logs, and restore points.

Response shapes (DSM 7.x, synology-api 0.9.x):
  * list_tasks()                -> data.tasks[]  (each with last_result, devices[], retention_policy, ...)
  * list_device_transfer_size() -> data.device_list[] of {device: {...}, transfer_list: [...]}
  * list_logs()                 -> data.logs[]  (log_time, log_level 0/1/2, log_type code, other_params)
  * list_tasks(include_versions=True) adds versions[] (restore points) to each task
"""

from __future__ import annotations

import json
import time
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict

from ..utils.formatters import format_size, format_timestamp, handle_synology_error, error_response

# Result status codes as returned by the API (see synology_api.core_active_backup docs).
STATUS = {1: "running", 2: "success", 3: "partial_success", 4: "fail", 5: "cancel"}
BACKUP_TYPE = {1: "vm", 2: "pc", 3: "physical_server", 4: "file_server", 5: "nas"}
LOG_LEVEL = {0: "error", 1: "warning", 2: "information"}
LOG_LEVEL_FILTERS = {"error", "warning", "information"}
# Never return credential-like fields that DSM includes in device/task records.
SECRET_KEYS = {"agent_token", "login_password", "mssql_password", "oracle_password"}
LOG_DETAIL_KEYS = ("status", "success_count", "error_count", "warning_count", "transfer_new_bytes", "volume_name")


class ABBNasInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    nas: Optional[str] = Field(default=None, description="NAS name")


class ABBTaskInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    task_id: int = Field(..., description="Active Backup task ID")
    nas: Optional[str] = Field(default=None, description="NAS name")


class ABBDeviceInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    device_id: int = Field(..., description="Device ID")
    nas: Optional[str] = Field(default=None, description="NAS name")


class ABBTaskListInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    nas: Optional[str] = Field(default=None, description="NAS name")
    problems_only: bool = Field(default=False, description="Only tasks whose last run was not a clean success")
    stale_days: Optional[int] = Field(
        default=None, ge=0, description="Only tasks whose last run ended at least this many days ago"
    )


class ABBLogInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    nas: Optional[str] = Field(default=None, description="NAS name")
    task_id: int = Field(default=-1, description="Limit to one task (-1 = all)")
    level: str = Field(default="", description="error, warning or information (empty = all)")
    keyword: str = Field(default="", description="Filter by keyword (task or device name)")
    limit: int = Field(default=50, ge=1, le=200, description="Entries to return (max 200)")
    offset: int = Field(default=0, ge=0, description="Skip this many entries")


def _clean(obj):
    """Recursively drop credential-like fields."""
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items() if k not in SECRET_KEYS}
    if isinstance(obj, list):
        return [_clean(v) for v in obj]
    return obj


def _ts(value):
    return format_timestamp(value) if value else "N/A"


def _age_days(epoch):
    return round((time.time() - epoch) / 86400, 1) if epoch else None


def _task_summary(task: dict) -> dict:
    last = task.get("last_result") or {}
    status = last.get("status")
    clean = status == 2 and not last.get("error_count") and not last.get("warning_count")
    return {
        "id": task.get("task_id"),
        "name": task.get("task_name"),
        "type": BACKUP_TYPE.get(task.get("backup_type"), task.get("backup_type")),
        "devices": [d.get("host_name") for d in task.get("devices", [])],
        "last_status": STATUS.get(status, f"code_{status}") if status is not None else "never_run",
        "last_start": _ts(last.get("time_start")),
        "last_end": _ts(last.get("time_end")),
        "last_run_age_days": _age_days(last.get("time_end")),
        "last_transferred": format_size(int(last["transfered_bytes"])) if last.get("transfered_bytes") else "N/A",
        "errors": last.get("error_count"),
        "warnings": last.get("warning_count"),
        "next_run": _ts(task.get("next_trigger_time")),
        "retention": task.get("retention_policy"),
        "_clean": clean,
    }


def _list_tasks(abb, **kwargs) -> list:
    result = abb.list_tasks(**kwargs)
    if not result or "data" not in result:
        raise RuntimeError("Could not list Active Backup tasks")
    return result["data"].get("tasks", [])


def _device_index(tasks: list) -> dict:
    """device_id -> [{task, last result}] built from the task list."""
    index: dict = {}
    for task in tasks:
        summary = _task_summary(task)
        for dev in task.get("devices", []):
            index.setdefault(dev.get("device_id"), []).append({
                "task_id": summary["id"],
                "task": summary["name"],
                "last_status": summary["last_status"],
                "last_end": summary["last_end"],
                "last_run_age_days": summary["last_run_age_days"],
                "agent_status": dev.get("agent_status"),
            })
    return index


def _device_row(dev: dict, index: dict) -> dict:
    return {
        "id": dev.get("device_id"),
        "name": dev.get("host_name"),
        "ip": dev.get("host_ip"),
        "os": dev.get("os_name"),
        "type": BACKUP_TYPE.get(dev.get("backup_type"), dev.get("backup_type")),
        "registered": _ts(dev.get("create_time")),
        "tasks": index.get(dev.get("device_id"), []),
    }


def _version_row(v: dict) -> dict:
    return {
        "version_id": v.get("version_id", v.get("id")),
        "folder": v.get("folder_name"),
        "start": _ts(v.get("time_start")),
        "end": _ts(v.get("time_end")),
        # Version status codes are not on the same scale as task-result codes; leave raw.
        "status_code": v.get("status"),
        "used_size": format_size(int(v["used_size"])) if v.get("used_size") else "N/A",
        "locked": v.get("locked"),
        "verify_status_code": v.get("verify_status"),
    }


def _log_row(log: dict) -> dict:
    params = log.get("other_params") or {}
    row = {
        "time": _ts(log.get("log_time")),
        "level": LOG_LEVEL.get(log.get("log_level"), log.get("log_level")),
        "log_type": log.get("log_type"),
        "task": log.get("task_name") or params.get("task_name"),
        "device": log.get("device_name") or params.get("device_name"),
        "error_code": log.get("error_code"),
    }
    detail = {k: params[k] for k in LOG_DETAIL_KEYS if params.get(k) not in (None, "")}
    if "status" in detail:
        detail["status"] = STATUS.get(detail["status"], detail["status"])
    if "transfer_new_bytes" in detail:
        detail["transfer_new_bytes"] = format_size(int(detail["transfer_new_bytes"]))
    if detail:
        row["detail"] = detail
    return row


def register_active_backup_tools(mcp, conn_mgr) -> None:
    """Register Active Backup for Business tools."""

    def _abb(nas=None):
        return conn_mgr.get_client("activebackup", nas)

    def _ro(title):
        return {"title": title, "readOnlyHint": True, "destructiveHint": False}

    @mcp.tool(name="synology_abb_list_tasks", annotations=_ro("List ABB Tasks"))
    async def synology_abb_list_tasks(params: ABBTaskListInput) -> str:
        """List Active Backup for Business tasks (PC, server, VM) with last result, age, transfer size,
        errors and next run. Use problems_only / stale_days to find tasks needing attention."""
        try:
            items = [_task_summary(t) for t in _list_tasks(_abb(params.nas))]
            total = len(items)
            if params.problems_only or params.stale_days is not None:
                def wanted(s):
                    bad = params.problems_only and not s["_clean"]
                    old = params.stale_days is not None and (
                        s["last_run_age_days"] is None or s["last_run_age_days"] >= params.stale_days
                    )
                    return bad or old
                items = [s for s in items if wanted(s)]
            for s in items:
                s.pop("_clean", None)
            return json.dumps({"count": len(items), "total_tasks": total, "tasks": items}, indent=2, default=str)
        except Exception as e:
            return handle_synology_error(e, "List ABB tasks")

    @mcp.tool(name="synology_abb_task_info", annotations=_ro("ABB Task Details"))
    async def synology_abb_task_info(params: ABBTaskInput) -> str:
        """Get details of one Active Backup task: config, schedule, retention, devices, versions, recent events."""
        try:
            abb = _abb(params.nas)
            tasks = _list_tasks(abb, task_id=params.task_id, include_versions=True)
            if not tasks:
                return error_response(f"Task {params.task_id} not found")
            task = tasks[0]
            schedule = dict(task.get("sched_content") or {})
            schedule.pop("backup_window", None)  # long per-hour bitmap, not useful
            versions = sorted(task.get("versions") or [], key=lambda v: v.get("time_end", 0), reverse=True)
            logs = abb.list_logs(task_id=params.task_id, limit=10).get("data", {}).get("logs", [])
            out = _task_summary(task)
            out.pop("_clean", None)
            out.update({
                "device_details": [
                    _clean({k: d.get(k) for k in ("device_id", "host_name", "host_ip", "os_name", "agent_status")})
                    for d in task.get("devices", [])
                ],
                "schedule": schedule,
                "target": {
                    "share": task.get("share_name"),
                    "dir": task.get("target_dir"),
                    "status": task.get("target_status"),
                },
                "version_count": task.get("version_count"),
                "latest_versions": [_version_row(v) for v in versions[:5]],
                "recent_log_events": [_log_row(entry) for entry in logs],
            })
            return json.dumps(out, indent=2, default=str)
        except Exception as e:
            return handle_synology_error(e, "ABB task info")

    @mcp.tool(name="synology_abb_list_devices", annotations=_ro("List ABB Devices"))
    async def synology_abb_list_devices(params: ABBNasInput) -> str:
        """List devices registered with Active Backup for Business, with the tasks protecting each."""
        try:
            abb = _abb(params.nas)
            result = abb.list_device_transfer_size()
            if not result or "data" not in result:
                return error_response("Could not list ABB devices")
            index = _device_index(_list_tasks(abb))
            rows = [_device_row(e.get("device", {}), index) for e in result["data"].get("device_list", [])]
            return json.dumps({"count": len(rows), "devices": rows}, indent=2, default=str)
        except Exception as e:
            return handle_synology_error(e, "List ABB devices")

    @mcp.tool(name="synology_abb_device_info", annotations=_ro("ABB Device Details"))
    async def synology_abb_device_info(params: ABBDeviceInput) -> str:
        """Get details of one registered backup device, including the tasks that protect it."""
        try:
            abb = _abb(params.nas)
            result = abb.list_device_transfer_size()
            if not result or "data" not in result:
                return error_response("Could not list ABB devices")
            for entry in result["data"].get("device_list", []):
                dev = entry.get("device", {})
                if dev.get("device_id") == params.device_id:
                    row = _device_row(dev, _device_index(_list_tasks(abb)))
                    row["details"] = _clean(dev)
                    return json.dumps(row, indent=2, default=str)
            return error_response(f"Device {params.device_id} not found")
        except Exception as e:
            return handle_synology_error(e, "ABB device info")

    @mcp.tool(name="synology_abb_logs", annotations=_ro("ABB Backup Logs"))
    async def synology_abb_logs(params: ABBLogInput) -> str:
        """Get recent Active Backup for Business log events, newest first. DSM returns event codes rather than
        message text, so each entry has log_type plus status, counts and transfer size where present."""
        try:
            level = params.level.lower()
            if level and level not in LOG_LEVEL_FILTERS:
                return error_response("level must be one of: error, warning, information")
            result = _abb(params.nas).list_logs(
                task_id=params.task_id, log_level=level, keyword=params.keyword,
                offset=params.offset, limit=params.limit,
            )
            if not result or "data" not in result:
                return error_response("Could not retrieve ABB logs")
            logs = result["data"].get("logs", [])
            return json.dumps({
                "returned": len(logs),
                "total_matching": result["data"].get("count"),
                "logs": [_log_row(entry) for entry in logs],
            }, indent=2, default=str)
        except Exception as e:
            return handle_synology_error(e, "ABB logs")

    @mcp.tool(name="synology_abb_restore_points", annotations=_ro("ABB Restore Points"))
    async def synology_abb_restore_points(params: ABBDeviceInput) -> str:
        """List stored backup versions (restore points) for a device, newest first."""
        try:
            abb = _abb(params.nas)
            refs = _device_index(_list_tasks(abb)).get(params.device_id, [])
            out = []
            for ref in refs:
                found = _list_tasks(abb, task_id=ref["task_id"], include_versions=True)
                versions = sorted((found[0].get("versions") or []) if found else [],
                                  key=lambda v: v.get("time_end", 0), reverse=True)
                out.append({
                    "task_id": ref["task_id"],
                    "task": ref["task"],
                    "version_count": len(versions),
                    "restore_points": [_version_row(v) for v in versions[:20]],
                })
            if not out:
                return error_response(f"No Active Backup task protects device {params.device_id}")
            return json.dumps({"device_id": params.device_id, "tasks": out}, indent=2, default=str)
        except Exception as e:
            return handle_synology_error(e, "ABB restore points")
