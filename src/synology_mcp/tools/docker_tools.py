"""Docker (Container Manager) tools — manage containers, images, and networks.

Covers: list containers, start/stop/restart, logs, images, networks, and resource usage.
"""

from __future__ import annotations

import json
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict

from ..utils.formatters import format_size, handle_synology_error, error_response


class DockerNasInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    nas: Optional[str] = Field(default=None, description="NAS name")


class ContainerInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    container_name: str = Field(..., description="Container name or ID", min_length=1)
    nas: Optional[str] = Field(default=None, description="NAS name")


class ContainerLogsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    container_name: str = Field(..., description="Container name or ID", min_length=1)
    tail: int = Field(default=100, description="Number of log lines to retrieve", ge=1, le=5000)
    nas: Optional[str] = Field(default=None, description="NAS name")


def register_docker_tools(mcp, conn_mgr) -> None:
    """Register Docker / Container Manager tools."""

    def _docker(nas=None):
        return conn_mgr.get_client("docker", nas)

    @mcp.tool(
        name="synology_docker_list_containers",
        annotations={"title": "List Docker Containers", "readOnlyHint": True, "destructiveHint": False},
    )
    async def synology_docker_list_containers(params: DockerNasInput) -> str:
        """List all Docker containers with status, image, ports, and resource usage."""
        try:
            docker = _docker(params.nas)
            result = docker.containers()
            if not result or "data" not in result:
                return error_response("Could not list containers")
            containers = result["data"].get("containers", result["data"])
            items = []
            if isinstance(containers, list):
                for c in containers:
                    items.append({
                        "name": c.get("name", c.get("names", [""])[0] if isinstance(c.get("names"), list) else ""),
                        "id": c.get("id", "")[:12],
                        "image": c.get("image", ""),
                        "status": c.get("status", c.get("state", "")),
                        "state": c.get("state", ""),
                    })
            return json.dumps({"containers": items, "count": len(items)}, indent=2, default=str)
        except Exception as e:
            return handle_synology_error(e, "List containers")

    @mcp.tool(
        name="synology_docker_start",
        annotations={"title": "Start Container", "readOnlyHint": False, "destructiveHint": False},
    )
    async def synology_docker_start(params: ContainerInput) -> str:
        """Start a stopped Docker container."""
        try:
            docker = _docker(params.nas)
            result = docker.start_container(container=params.container_name)
            return json.dumps({"status": "success", "action": "started", "container": params.container_name}, indent=2)
        except Exception as e:
            return handle_synology_error(e, "Start container")

    @mcp.tool(
        name="synology_docker_stop",
        annotations={"title": "Stop Container", "readOnlyHint": False, "destructiveHint": False},
    )
    async def synology_docker_stop(params: ContainerInput) -> str:
        """Stop a running Docker container."""
        try:
            docker = _docker(params.nas)
            result = docker.stop_container(container=params.container_name)
            return json.dumps({"status": "success", "action": "stopped", "container": params.container_name}, indent=2)
        except Exception as e:
            return handle_synology_error(e, "Stop container")

    @mcp.tool(
        name="synology_docker_restart",
        annotations={"title": "Restart Container", "readOnlyHint": False, "destructiveHint": False},
    )
    async def synology_docker_restart(params: ContainerInput) -> str:
        """Restart a Docker container."""
        try:
            docker = _docker(params.nas)
            docker.restart_container(container=params.container_name)
            return json.dumps({"status": "success", "action": "restarted", "container": params.container_name}, indent=2)
        except Exception as e:
            return handle_synology_error(e, "Restart container")

    @mcp.tool(
        name="synology_docker_logs",
        annotations={"title": "Container Logs", "readOnlyHint": True, "destructiveHint": False},
    )
    async def synology_docker_logs(params: ContainerLogsInput) -> str:
        """Get recent logs from a Docker container."""
        try:
            docker = _docker(params.nas)
            result = docker.get_logs(name=params.container_name)
            if not result or "data" not in result:
                return error_response(f"Could not get logs for '{params.container_name}'")
            logs = result["data"].get("logs", result["data"])
            if isinstance(logs, list):
                logs = logs[-params.tail:]
            return json.dumps({"container": params.container_name, "logs": logs}, indent=2, default=str)
        except Exception as e:
            return handle_synology_error(e, "Container logs")

    @mcp.tool(
        name="synology_docker_list_images",
        annotations={"title": "List Docker Images", "readOnlyHint": True, "destructiveHint": False},
    )
    async def synology_docker_list_images(params: DockerNasInput) -> str:
        """List all Docker images on the NAS."""
        try:
            docker = _docker(params.nas)
            result = docker.downloaded_images()
            if not result or "data" not in result:
                return error_response("Could not list images")
            images = result["data"].get("images", result["data"])
            items = []
            if isinstance(images, list):
                for img in images:
                    items.append({
                        "repository": img.get("repository", ""),
                        "tag": img.get("tag", ""),
                        "size": format_size(int(img.get("size", 0))),
                        "created": img.get("created", ""),
                    })
            return json.dumps({"images": items, "count": len(items)}, indent=2, default=str)
        except Exception as e:
            return handle_synology_error(e, "List images")

    @mcp.tool(
        name="synology_docker_list_networks",
        annotations={"title": "List Docker Networks", "readOnlyHint": True, "destructiveHint": False},
    )
    async def synology_docker_list_networks(params: DockerNasInput) -> str:
        """List all Docker networks on the NAS."""
        try:
            docker = _docker(params.nas)
            result = docker.network()
            if not result or "data" not in result:
                return error_response("Could not list networks")
            return json.dumps(result["data"], indent=2, default=str)
        except Exception as e:
            return handle_synology_error(e, "List networks")

    @mcp.tool(
        name="synology_docker_resource_usage",
        annotations={"title": "Docker Resource Usage", "readOnlyHint": True, "destructiveHint": False},
    )
    async def synology_docker_resource_usage(params: DockerNasInput) -> str:
        """Get resource usage summary for all Docker containers."""
        try:
            docker = _docker(params.nas)
            result = docker.container_resources()
            if not result or "data" not in result:
                return error_response("Could not retrieve Docker resource usage")
            return json.dumps(result["data"], indent=2, default=str)
        except Exception as e:
            return handle_synology_error(e, "Docker resources")
