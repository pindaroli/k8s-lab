name: Build and Publish <app>-mcp Container

on:
  push:
    branches:
      - main
    paths:
      - 'docker/<app>-mcp/**'
      - '.github/workflows/docker-<app>-mcp.yml'
  workflow_dispatch:
    inputs:
      image_tag:
        description: 'Tag semantico per l''immagine (es. 1.0.0)'
        required: true
        default: '1.0.0'

permissions:
  contents: read
  packages: write

jobs:
  build-and-push:
    name: Build & Push <app>-mcp to GHCR
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to GitHub Container Registry (GHCR)
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract Docker Metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ghcr.io/${{ github.repository_owner }}/<app>-mcp
          tags: |
            type=raw,value=${{ inputs.image_tag || '<app_version>' }}
            type=raw,value=latest,enable=${{ github.ref == 'refs/heads/main' }}
            type=sha,prefix=sha-,format=short

      - name: Build and Push Image
        uses: docker/build-push-action@v5
        with:
          context: ./docker/<app>-mcp
          file: ./docker/<app>-mcp/Dockerfile
          platforms: linux/amd64
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
