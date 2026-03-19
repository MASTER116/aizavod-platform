"""Project Deployer — pushes project to GitHub via API and deploys demo.

Uses PyGithub API (no git CLI needed) for:
- Creating GitHub repository
- Uploading all project files
- Enabling GitHub Pages
"""
from __future__ import annotations

import base64
import logging
import os
import subprocess
from pathlib import Path

from github import Github, GithubException

logger = logging.getLogger("aizavod.project_deployer")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME", "azatmaster")


def _get_github() -> Github:
    return Github(GITHUB_TOKEN)


async def deploy_project(
    project_dir: str,
    project_name: str,
    description: str = "",
    private: bool = False,
) -> dict:
    """Deploy project to GitHub and enable GitHub Pages.

    Returns dict with 'github_url', 'demo_url', 'success'.
    """
    pdir = Path(project_dir)
    if not pdir.exists():
        return {"success": False, "error": f"Project dir not found: {project_dir}"}

    g = _get_github()
    user = g.get_user()

    # Step 1: Create or get repo
    repo = None
    try:
        repo = g.get_repo(f"{GITHUB_USERNAME}/{project_name}")
        logger.info("Repo already exists: %s", repo.full_name)
    except GithubException:
        try:
            repo = user.create_repo(
                project_name,
                description=description[:200],
                private=private,
                auto_init=False,
            )
            logger.info("Created repo: %s", repo.full_name)
        except GithubException as e:
            return {"success": False, "error": f"Failed to create repo: {e}"}

    if not repo:
        return {"success": False, "error": "Could not access or create repo"}

    # Step 2: Upload all files via GitHub API
    uploaded = 0
    errors = []

    # Collect all files
    files_to_upload = []
    for fpath in pdir.rglob("*"):
        if fpath.is_file():
            rel = str(fpath.relative_to(pdir)).replace("\\", "/")
            # Skip hidden/temp files
            if rel.startswith(".") or "__pycache__" in rel or "node_modules" in rel:
                continue
            files_to_upload.append((rel, fpath))

    # Upload files one by one (GitHub API doesn't support batch)
    for rel_path, abs_path in files_to_upload:
        try:
            content = abs_path.read_bytes()
            # Try to decode as text, fall back to base64
            try:
                text_content = content.decode("utf-8")
                is_binary = False
            except UnicodeDecodeError:
                is_binary = True

            # Check if file exists in repo
            try:
                existing = repo.get_contents(rel_path)
                if is_binary:
                    repo.update_file(
                        rel_path,
                        f"Update {rel_path}",
                        content,
                        existing.sha,
                    )
                else:
                    repo.update_file(
                        rel_path,
                        f"Update {rel_path}",
                        text_content,
                        existing.sha,
                    )
            except GithubException:
                # File doesn't exist, create it
                if is_binary:
                    repo.create_file(
                        rel_path,
                        f"Add {rel_path}",
                        content,
                    )
                else:
                    repo.create_file(
                        rel_path,
                        f"Add {rel_path}",
                        text_content,
                    )

            uploaded += 1
        except Exception as e:
            errors.append(f"{rel_path}: {e}")
            logger.error("Failed to upload %s: %s", rel_path, e)

    logger.info("Uploaded %d files, %d errors", uploaded, len(errors))

    # Step 3: Enable GitHub Pages if there's an index.html
    demo_url = ""
    has_index = (pdir / "index.html").exists()

    if has_index:
        try:
            # Enable Pages via API
            repo._requester.requestJsonAndCheck(
                "POST",
                f"{repo.url}/pages",
                input={"source": {"branch": "main", "path": "/"}},
            )
            demo_url = f"https://{GITHUB_USERNAME}.github.io/{project_name}/"
            logger.info("GitHub Pages enabled: %s", demo_url)
        except Exception as e:
            logger.warning("Could not enable Pages: %s", e)
            # Pages might already be enabled
            demo_url = f"https://{GITHUB_USERNAME}.github.io/{project_name}/"

    repo_url = f"https://github.com/{GITHUB_USERNAME}/{project_name}"

    return {
        "success": uploaded > 0,
        "github_url": repo_url,
        "demo_url": demo_url,
        "files_uploaded": uploaded,
        "errors": errors[:5],
        "push_output": f"Uploaded {uploaded} files" + (f", {len(errors)} errors" if errors else ""),
    }


async def deploy_to_server(
    project_dir: str,
    project_name: str,
    port: int = 0,
) -> dict:
    """Deploy project as a Docker container on the server."""
    pdir = Path(project_dir)

    if not (pdir / "Dockerfile").exists():
        if (pdir / "requirements.txt").exists():
            dockerfile = (
                "FROM python:3.12-slim\n"
                "WORKDIR /app\n"
                "COPY requirements.txt .\n"
                "RUN pip install -r requirements.txt\n"
                "COPY . .\n"
                "EXPOSE 8080\n"
                'CMD ["python", "app.py"]\n'
            )
        elif (pdir / "package.json").exists():
            dockerfile = (
                "FROM node:20-slim\n"
                "WORKDIR /app\n"
                "COPY package*.json .\n"
                "RUN npm install\n"
                "COPY . .\n"
                "EXPOSE 8080\n"
                'CMD ["npm", "start"]\n'
            )
        else:
            dockerfile = (
                "FROM nginx:alpine\n"
                "COPY . /usr/share/nginx/html/\n"
                "EXPOSE 80\n"
            )
        (pdir / "Dockerfile").write_text(dockerfile)

    if port == 0:
        import socket
        with socket.socket() as s:
            s.bind(("", 0))
            port = s.getsockname()[1]

    container_name = f"hackathon-{project_name}"

    def _run(cmd: str) -> str:
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=120
            )
            return (result.stdout + result.stderr).strip()
        except Exception as e:
            return f"ERROR: {e}"

    _run(f"docker stop {container_name} 2>/dev/null; docker rm {container_name} 2>/dev/null")

    build_result = _run(f"cd {pdir} && docker build -t {container_name} . 2>&1")
    run_result = _run(
        f"docker run -d --name {container_name} "
        f"-p {port}:8080 --restart unless-stopped "
        f"{container_name} 2>&1"
    )

    return {
        "success": "error" not in build_result.lower()[-200:],
        "container": container_name,
        "port": port,
        "demo_url": f"http://72.56.127.52:{port}/",
        "build_output": build_result[-500:],
    }
