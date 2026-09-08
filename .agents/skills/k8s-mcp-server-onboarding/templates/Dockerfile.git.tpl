# WARNING: Upstream repository <owner>/<repo> has no formal release tags.
# In accordance with mcp-upstream-tracking-pattern (Rule 2: Fallback Mono-Branch),
# auto-adopting single active branch: main (latest commit: <commit_sha>).
ARG UPSTREAM_REF=<commit_sha>

FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install requirements from checked out upstream directory
COPY upstream/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Create unprivileged non-root user (UID 1000)
RUN useradd -u 1000 -m -s /bin/bash appuser && \
    chown -R appuser:appuser /app

# Copy upstream application code
COPY --chown=appuser:appuser upstream/*.py /app/

# Copy custom entrypoint for ToolHive stdio / HTTP compatibility
COPY --chown=appuser:appuser entrypoint.py /app/entrypoint.py

USER appuser

# ToolHive executes the container and communicates via stdio
ENTRYPOINT ["python", "entrypoint.py"]
