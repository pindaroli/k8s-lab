#!/usr/bin/env python3
# Launcher dinamico multi-progetto e pluggable per llmwiki MCP
import os
import sys

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

    # 2. Root del progetto aperto (CWD), non un path fisso.
    #    Env WIKI_PATH / LLMWIKI_BASE_DIR vincono solo se valorizzate a una directory esistente.
    cwd = os.getcwd()
    target_base_dir = os.getenv("WIKI_PATH") or os.getenv("LLMWIKI_BASE_DIR")
    if not target_base_dir or not os.path.isdir(target_base_dir):
        if os.path.basename(cwd) == "wiki" and (
            os.path.isdir(os.path.join(cwd, "_meta")) or os.path.isdir(os.path.join(cwd, "concepts"))
        ):
            target_base_dir = os.path.dirname(cwd)
        elif cwd != "/" and (os.path.isdir(os.path.join(cwd, "wiki")) or os.path.isdir(os.path.join(cwd, "raw"))):
            target_base_dir = cwd
        else:
            # Fallback automatico alla root del repo contenente questo script (scripts/llmwiki/ -> ../..)
            script_repo_root = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", ".."))
            target_base_dir = script_repo_root if os.path.isdir(script_repo_root) else cwd

    os.environ["WIKI_PATH"] = target_base_dir

    # Log diagnostico su STDERR (mai su STDOUT che è riservato a JSON-RPC)
    sys.stderr.write(f"[llmwiki-launcher] Active CWD: {cwd}\n")
    sys.stderr.write(f"[llmwiki-launcher] Target Base Dir: {target_base_dir}\n")
    sys.stderr.write(f"[llmwiki-launcher] LLM Endpoint: {base_url} (Model: {model})\n")
    sys.stderr.flush()

    # 3. Avvio di llmwiki con la base-dir del progetto corrente
    cmd = [sys.executable, "-m", "llmwiki", "--base-dir", target_base_dir]
    if len(sys.argv) > 1:
        cmd.extend(sys.argv[1:])

    os.execvp(cmd[0], cmd)

if __name__ == "__main__":
    main()
