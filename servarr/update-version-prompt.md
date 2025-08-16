# Update Servarr Components to Latest Versions

Find all the latest stable versions of Servarr components used in `/Users/olindo/prj/k8s-lab/servarr/arr-values.yaml` and update them.

## Task:
1. Read the current `arr-values.yaml` to identify current versions
2. Find latest stable versions from LinuxServer.io Docker Hub registry (`lscr.io/linuxserver/`)
3. Use specific version numbers (not "latest" tags) from Docker Hub API
4. Update the values file with new image tags including comments showing previous versions

## Components to check:
- jellyfin, sonarr, qbittorrent, prowlarr, radarr, lidarr, bazarr, readarr, jellyseerr

## Output format:
Add `image.tag` overrides with comments showing previous versions:
```yaml
componentname:
  image:
    tag: "x.y.z"  # was: old.version
```

## Requirements:
- Only use stable numbered releases (avoid nightly/develop/latest tags)
- Add comments showing previous versions for reference
- Update both enabled and disabled services
- Use Docker Hub API to verify latest stable versions correspond to "latest" tag