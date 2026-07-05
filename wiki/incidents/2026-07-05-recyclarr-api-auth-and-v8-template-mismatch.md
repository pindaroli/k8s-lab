---
title: "Recyclarr API Authentication Failure and v8 Template Mismatch"
type: incident
status: archived
certified_for_ai: false
date: 2026-07-05
severity: P3
resolved: true
resolved_at: 2026-07-05T08:14:00Z
tags:
  - "#incident"
  - "#recyclarr"
  - "#radarr"
---

# Incident: Recyclarr API Authentication Failure and v8 Template Mismatch
**Date**: 2026-07-05
**Status**: RESOLVED (API key realigned with SOPS source; Helm chart and values upgraded to Recyclarr v8 standards)
**Severity**: Medium (Prevented Recyclarr from syncing custom formats and quality profiles into Radarr)

## 🔍 Diagnosis
During the validation of the Recyclarr quality automation stack in Radarr:
1. **API Authentication Failure (401 Unauthorized)**: The Recyclarr sync job was failing silently or skipping sync because the API Key configured in the Kubernetes Secret `servarr-api-keys` (specifically the key `radarr-api-key`) was incorrect (`0fb8a908d549466585c98632b5275b47`) due to a character inversion (positions 7 and 8 had `08` instead of `80`). The correct API key saved in Radarr's `/config/config.xml` (and in the SOPS encrypted repository source) was `0fb8a980d549466585c98632b5275b47`.
2. **Missing Custom Formats**: Because of the authentication failure, the Custom Formats API endpoint of Radarr (`/api/v3/customformat`) was returning an empty array `[]`.
3. **v8 Template Incompatibility**: The Kubernetes CronJob was configured to run a legacy binary (`recyclarr:6.0`), but it dynamically cloned the latest TRaSH Guides templates (which target Recyclarr v8). In v8, all official `include:` templates (such as `radarr-quality-definition-movie` and `radarr-custom-formats-*`) have been removed in favor of **Guide-Backed Quality Profiles** using `trash_id`. Attempting to run v8 templates on the v6 binary caused a parsing crash (`YamlIncludeException` / property `assign_scores_to` not found).

## 🛠️ Actions Taken & Resolution

### 1. API Secret Realignment
* Decrypted the repository master secret `secrets-sops/servarr-api-keys.enc.yaml` (which already had the correct key `a980`).
* Re-applied the secret to the cluster using SOPS:
  ```bash
  sops -d secrets-sops/servarr-api-keys.enc.yaml | kubectl apply -f -
  ```

### 2. Upgrading Chart and Values to Recyclarr v8
* **Chart Template Upgrade**: Modified `charts/servarr/templates/recyclarr/configmap.yaml` in the `pindaroli-arr-helm` repository to support the modern `quality_definition` and `quality_profiles` blocks via `toYaml`.
* **Default Values Alignment**: Modified `charts/servarr/values.yaml` in the `pindaroli-arr-helm` repository to remove the obsolete `include:` blocks and replaced them with the v8 native configuration using TRaSH Guides `trash_id` (Remux 2160p: `fd161a61e3ab826d3a22d53f935696dd` and HD Bluray: `d1d67249d3890e49bc12e275d989a7e9`).
* **Version Bump**: Bumped the chart version in `Chart.yaml` to `1.2.10` and pushed the changes to triggering the release pipeline.
* **Production values update**: Updated the production values file `servarr/arr-values.yaml` in the `k8s-lab` repository to reflect the new native v8 config.

### 3. Deploy and Outage Bypass
* Due to a transient error on GitHub Pages (`pages-build-deployment` failing) preventing the immediate propagation of the new chart `1.2.10` web package, deployed the upgrade directly using the local path:
  ```bash
  helm upgrade servarr /Users/olindo/prj/pindaroli-arr-helm/charts/servarr -n arr -f servarr/arr-values.yaml
  ```

### 4. Sync Job Verification
* Created a manual test job:
  ```bash
  kubectl create job --from=cronjob/servarr-recyclarr recyclarr-test-sync -n arr
  ```
* Monitored the pod logs which showed 59 custom formats successfully created and 2 profiles updated with the correct scores.
* Deleted the test job.

## 🧪 Verification Results
* **Radarr API Verification**: Ran curl against Radarr API using the correct key:
  ```bash
  curl -s -k -H "X-Api-Key: 0fb8a980d549466585c98632b5275b47" https://radarr-internal.pindaroli.org/api/v3/customformat | jq '. | length'
  ```
  Result returned **`59`**, confirming that the 59 custom formats are present and synced.

## 🔗 References
* [[Talos_Cluster]]
* [arr-values.yaml](file:///Users/olindo/prj/k8s-lab/servarr/arr-values.yaml)
* [values.yaml](file:///Users/olindo/prj/pindaroli-arr-helm/charts/servarr/values.yaml)
* [configmap.yaml](file:///Users/olindo/prj/pindaroli-arr-helm/charts/servarr/templates/recyclarr/configmap.yaml)
