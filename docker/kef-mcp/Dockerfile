FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install requirements from upstream
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
