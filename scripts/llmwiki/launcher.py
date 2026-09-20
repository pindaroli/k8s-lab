#!/usr/bin/env python3
# Launcher dinamico multi-progetto e pluggable per llmwiki MCP
import os
import sys


def _abspath(path: str) -> str:
    return os.path.abspath(os.path.expanduser(path))


def _is_wiki_dir(path: str) -> bool:
    """True if path is a wiki/ folder, not the project root."""
    if os.path.basename(path) != "wiki":
        return False
    return any(
        os.path.isdir(os.path.join(path, marker))
        for marker in ("_meta", "concepts", "entities")
    )


def _is_project_root(path: str) -> bool:
    """Project root = directory that owns wiki/ and/or raw/. Never $HOME."""
    if not path or path in ("/", _abspath("~")):
        return False
    return os.path.isdir(os.path.join(path, "wiki")) or os.path.isdir(os.path.join(path, "raw"))


def _as_project_root(path: str) -> str:
    path = _abspath(path)
    if _is_wiki_dir(path):
        return os.path.dirname(path)
    return path


def resolve_project_root(cwd: str) -> str:
    """<project> so llmwiki uses <project>/wiki and <project>/raw."""
    env = os.getenv("WIKI_PATH") or os.getenv("LLMWIKI_BASE_DIR")
    if env and os.path.isdir(env):
        return _as_project_root(env)

    cwd = _abspath(cwd)
    if _is_wiki_dir(cwd):
        return os.path.dirname(cwd)
    if _is_project_root(cwd):
        return cwd

    script_repo_root = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", ".."))
    return script_repo_root if os.path.isdir(script_repo_root) else cwd


def main():
    # 1. Mappatura trasparente variabili LLM generiche -> upstream
    base_url = os.getenv("LLM_BASE_URL", "http://10.10.20.100:11434/v1")
    api_key = os.getenv("LLM_API_KEY", "ollama")
    model = os.getenv("LLM_MODEL", "deepseek-r1:32b")

    os.environ["OPENAI_BASE_URL"] = base_url
    os.environ["OPENAI_API_KEY"] = api_key
    os.environ["OPENAI_MODEL"] = model
    os.environ["LLMBASE_BASE_URL"] = base_url
    os.environ["LLMBASE_API_KEY"] = api_key
    os.environ["LLMBASE_MODEL"] = model
    os.environ["MODEL"] = model

    # 2. --base-dir è sempre la root del progetto, mai .../wiki.
    cwd = os.getcwd()
    target_base_dir = resolve_project_root(cwd)
    os.environ["WIKI_PATH"] = target_base_dir

    # Log diagnostico su STDERR (mai su STDOUT che è riservato a JSON-RPC)
    sys.stderr.write(f"[llmwiki-launcher] Active CWD: {cwd}\n")
    sys.stderr.write(f"[llmwiki-launcher] Target Base Dir: {target_base_dir}\n")
    sys.stderr.write(f"[llmwiki-launcher] Wiki: {os.path.join(target_base_dir, 'wiki')}\n")
    sys.stderr.write(f"[llmwiki-launcher] Raw: {os.path.join(target_base_dir, 'raw')}\n")
    sys.stderr.write(f"[llmwiki-launcher] LLM Endpoint: {base_url} (Model: {model})\n")
    sys.stderr.flush()

    # 3. Avvio di llmwiki con la base-dir del progetto corrente
    cmd = [sys.executable, "-m", "llmwiki", "--base-dir", target_base_dir]
    if len(sys.argv) > 1:
        cmd.extend(sys.argv[1:])

    os.execvp(cmd[0], cmd)


if __name__ == "__main__":
    main()
