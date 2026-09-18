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

    # 2. Risoluzione dinamica della cartella wiki del progetto attivo (CWD)
    cwd = os.getcwd()
    wiki_subpath = os.path.join(cwd, "wiki")
    target_base_dir = wiki_subpath if os.path.isdir(wiki_subpath) else cwd

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
