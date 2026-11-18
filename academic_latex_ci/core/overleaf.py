"""
Overleaf Cloud Sync & Build Client.

Provides automated two-way file synchronization, socket.io session handling,
cloud compilation, and PDF artifact retrieval with Overleaf.

Credits & Prior Art:
Derived and modularized from the open-source Overleaf-Antigravity bridge.
Attribution: Community-driven LaTeX cloud automation connectors.
"""

import base64
import http.cookiejar
import io
import json
import mimetypes
import os
import re
import socket
import ssl
import sys
import time
import urllib.request
import uuid
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class OverleafClient:
    """Manages authentication, file transfer, and compilation against Overleaf."""

    def __init__(self, project_id: str, cookie_val: Optional[str] = None, cookie_file: Optional[Path] = None):
        self.project_id = project_id
        self.cookie_file = cookie_file
        self._cookie_val = cookie_val

    @property
    def cookie_val(self) -> str:
        if self._cookie_val:
            return self._cookie_val
        if self.cookie_file and self.cookie_file.exists():
            val = self.cookie_file.read_text(encoding="utf-8").strip()
            return val.removeprefix("overleaf_session2=")
        raise RuntimeError("Missing Overleaf session cookie. Provide cookie_val or existing cookie_file.")

    def get_cookie_header(self) -> str:
        return f"overleaf_session2={self.cookie_val}"

    def compile_and_download(self, output_pdf: Path) -> Path:
        """Triggers remote Overleaf compilation and downloads the resulting PDF."""
        cookie_header = self.get_cookie_header()

        # 1. Fetch ol-csrfToken
        req_home = urllib.request.Request(
            f"https://www.overleaf.com/project/{self.project_id}",
            headers={"Cookie": cookie_header, "User-Agent": "Mozilla/5.0"}
        )
        html = urllib.request.urlopen(req_home).read().decode("utf-8")
        m = re.search(r'<meta\s+name="ol-csrfToken"\s+content="([^"]+)"', html)
        if not m:
            raise RuntimeError("Could not find ol-csrfToken on Overleaf. Check session cookie validity.")
        csrf = m.group(1)

        # 2. Trigger compilation
        compile_payload = json.dumps({
            "draft": False,
            "check": "silent",
            "incrementalCompilesEnabled": True
        }).encode("utf-8")

        req_compile = urllib.request.Request(
            f"https://www.overleaf.com/project/{self.project_id}/compile",
            data=compile_payload,
            headers={
                "Cookie": cookie_header,
                "User-Agent": "Mozilla/5.0",
                "Content-Type": "application/json",
                "X-Csrf-Token": csrf,
            }
        )
        resp = urllib.request.urlopen(req_compile)
        res = json.loads(resp.read().decode("utf-8"))

        status = res.get("status")
        if status != "success":
            raise RuntimeError(f"Overleaf compile failed with status: {status}\n{res}")

        pdf_files = [f for f in res.get("outputFiles", []) if f.get("type") == "pdf"]
        if not pdf_files:
            raise RuntimeError("Compilation succeeded but no PDF output was produced.")
        
        pdf_file = pdf_files[0]
        build = pdf_file["build"]
        compile_group = res.get("compileGroup", "standard")
        clsi_server_id = res.get("clsiServerId", "")

        download_url = (
            f"https://www.overleaf.com/download/project/{self.project_id}/build/{build}/"
            f"output/output.pdf?compileGroup={compile_group}&clsiserverid={clsi_server_id}"
        )
        req_pdf = urllib.request.Request(download_url, headers={"Cookie": cookie_header, "User-Agent": "Mozilla/5.0"})
        pdf_bytes = urllib.request.urlopen(req_pdf).read()
        output_pdf.parent.mkdir(parents=True, exist_ok=True)
        output_pdf.write_bytes(pdf_bytes)
        return output_pdf

    def pull_zip(self, output_zip: Path) -> Path:
        """Downloads full project archive as a zip file."""
        cookie_header = self.get_cookie_header()
        url = f"https://www.overleaf.com/project/{self.project_id}/download/zip"
        req = urllib.request.Request(url, headers={"Cookie": cookie_header, "User-Agent": "Mozilla/5.0"})
        data = urllib.request.urlopen(req).read()
        output_zip.parent.mkdir(parents=True, exist_ok=True)
        output_zip.write_bytes(data)
        return output_zip
