#!/usr/bin/env zsh

echo "🔍 Cercando oggetti Kubernetes in stato Terminating..."
echo

# Elenco delle risorse da controllare
types=("pods" "pvc" "pv" "deployments" "replicasets" "services" "jobs" "statefulsets" "daemonsets")

for res in $types; do
  echo "▶️  $res:"
  output=$(kubectl get $res --all-namespaces -o json 2>/dev/null \
    | jq -r '.items[] | select(.metadata.deletionTimestamp != null) | "\(.kind) \(.metadata.name) [ns:\(.metadata.namespace)]"')

  if [[ -z "$output" ]]; then
    echo "  ✅ Nessun oggetto in Terminating"
  else
    echo "$output"
  fi
  echo
done
