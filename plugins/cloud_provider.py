"""JARVIS plugin - cloud provider basics (AWS/Azure/GCP)."""
from __future__ import annotations

import subprocess
import sys

from core import outcome


PLUGIN = {
    "name": "cloud_provider",
    "description": "Basic cloud operations: AWS (S3/EC2), Azure (VMs/storage), GCP (compute/storage) via CLIs.",
    "brief": "Cloud: AWS/Azure/GCP basics via CLI.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "provider": {"type": "STRING", "description": "aws|azure|gcp"},
            "action": {"type": "STRING", "description": "s3_list|ec2_list|az_vm_list|az_storage_list|gcloud_compute_list|gcloud_storage_list"},
            "bucket": {"type": "STRING", "description": "Bucket name (S3/GCS)."},
            "region": {"type": "STRING", "description": "Region."},
        },
        "required": ["provider", "action"],
    },
    "tier": "extra",
}


def _run(cmd):
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0)
        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        return proc.returncode, (out + ("\n" + err if err else ""))[:4000]
    except FileNotFoundError:
        return 1, "CLI not found on PATH"
    except Exception as e:
        return 1, str(e)


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    provider = (params.get("provider") or "").lower()
    action = (params.get("action") or "").lower()
    region = params.get("region", "")
    if provider == "aws":
        if action == "s3_list":
            bucket = params.get("bucket", "")
            cmd = ["aws", "s3", "ls", f"s3://{bucket}"] if bucket else ["aws", "s3", "ls"]
            if region:
                cmd += ["--region", region]
        elif action == "ec2_list":
            cmd = ["aws", "ec2", "describe-instances", "--query", "Reservations[].Instances[].{ID:InstanceId,State:State.Name,Type:InstanceType}", "--output", "table"]
            if region:
                cmd += ["--region", region]
        else:
            return outcome.failed("cloud_provider", f"unknown aws action: {action}")
    elif provider == "azure":
        if action == "az_vm_list":
            cmd = ["az", "vm", "list", "-o", "table"]
        elif action == "az_storage_list":
            cmd = ["az", "storage", "account", "list", "-o", "table"]
        else:
            return outcome.failed("cloud_provider", f"unknown azure action: {action}")
    elif provider == "gcp":
        if action == "gcloud_compute_list":
            cmd = ["gcloud", "compute", "instances", "list"]
        elif action == "gcloud_storage_list":
            cmd = ["gcloud", "storage", "ls"]
        else:
            return outcome.failed("cloud_provider", f"unknown gcp action: {action}")
    else:
        return outcome.failed("cloud_provider", f"unknown provider: {provider}")
    code, out = _run(cmd)
    return (outcome.done if code == 0 else outcome.failed)("cloud_provider", note=out[:400], output=out)
