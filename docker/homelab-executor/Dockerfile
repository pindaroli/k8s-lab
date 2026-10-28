# Multi-architecture Dockerfile for Homelab Executor
ARG PYTHON_BASE_IMAGE=python:3.12-slim
FROM ${PYTHON_BASE_IMAGE}

ARG TARGETARCH
ARG APP_VERSION=1.0.0

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_VERSION=${APP_VERSION} \
    SOPS_AGE_KEY_FILE=/home/executor/.config/sops/age/keys.txt \
    ANSIBLE_CONFIG=/app/ansible/ansible.cfg

# 1. Install system utilities and dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    tini \
    gosu \
    openssh-server \
    openssh-client \
    rsync \
    jq \
    curl \
    dnsutils \
    iputils-ping \
    socat \
    wakeonlan \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 2. Download dynamic binaries based on TARGETARCH (amd64 / arm64)
RUN ARCH="${TARGETARCH}"; \
    if [ -z "$ARCH" ]; then ARCH="$(dpkg --print-architecture)"; fi; \
    echo "Installing architecture-specific binaries for arch: ${ARCH}"; \
    # sops \
    SOPS_VERSION="v3.9.4"; \
    curl -fsSL "https://github.com/getsops/sops/releases/download/${SOPS_VERSION}/sops-${SOPS_VERSION}.linux.${ARCH}" -o /usr/local/bin/sops && \
    chmod 0755 /usr/local/bin/sops; \
    # kubectl \
    KUBECTL_VERSION="v1.32.0"; \
    curl -fsSL "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/${ARCH}/kubectl" -o /usr/local/bin/kubectl && \
    chmod 0755 /usr/local/bin/kubectl; \
    # talosctl \
    TALOSCTL_VERSION="v1.9.4"; \
    curl -fsSL "https://github.com/siderolabs/talos/releases/download/${TALOSCTL_VERSION}/talosctl-linux-${ARCH}" -o /usr/local/bin/talosctl && \
    chmod 0755 /usr/local/bin/talosctl; \
    # verify installed binaries \
    sops --version && kubectl version --client && talosctl version --client

# 3. Create executor user and group (UID 1000, GID 1000) with unlocked account for SSH pubkey
RUN groupadd -g 1000 executor && \
    useradd -u 1000 -g 1000 -m -s /bin/bash executor && \
    usermod -p '*' executor

# 4. SSH daemon & client configuration
COPY docker/homelab-executor/sshd_config /etc/ssh/sshd_config
COPY docker/homelab-executor/ssh_config /etc/ssh/ssh_config

# 5. Install Python dependencies
COPY docker/homelab-executor/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm -f /tmp/requirements.txt

# 6. Immutable Application Snapshot
WORKDIR /app

COPY --chown=root:root scripts/ /app/scripts/
COPY --chown=root:root ansible/ /app/ansible/
COPY --chown=root:root rete.json /app/rete.json
COPY --chown=root:root storage.json /app/storage.json
COPY --chown=root:root secrets-sops/ /app/secrets-sops/
COPY --chown=root:root schemas/ /app/schemas/
COPY --chown=root:root docker/homelab-executor/server/ /app/server/
COPY --chown=root:root docker/homelab-executor/entrypoint.sh /app/entrypoint.sh

# Harden filesystem permissions (root:root, 0755)
RUN chmod -R 0755 /app && \
    chmod 0755 /app/entrypoint.sh

# Expose ports
EXPOSE 22 8000

# Supervision entrypoint via tini
ENTRYPOINT ["/usr/bin/tini", "--", "/app/entrypoint.sh"]
