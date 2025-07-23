#!/bin/zsh

# Percorso delle cartelle pod in MicroK8s
PODS_PATH="/var/snap/microk8s/common/var/lib/kubelet/pods"
UID_FILE="$1"

if [[ ! -f "$UID_FILE" ]]; then
  echo "❌ Errore: specifica un file con gli UID attivi come primo argomento."
  echo "Esempio: $0 uid_attivi.txt"
  exit 1
fi

# Carica UID attivi in array ZSH
active_uids=("${(@f)$(<"$UID_FILE")}")

echo "🔍 Controllo cartelle pod in: $PODS_PATH"
echo

# Scorri tutte le cartelle
for pod_dir in "$PODS_PATH"/*; do
  [[ -d "$pod_dir" ]] || continue

  pod_uid="${pod_dir:t}"

  if [[ ! "${active_uids[@]}" =~ "$pod_uid" ]]; then
    echo "⚠️  Pod UID $pod_uid NON trovato tra quelli attivi."
    echo "   Cartella residua presente: $pod_dir"
    echo "   👉 Comando per rimozione:"
    echo "   sudo rm -rf \"$pod_dir\""
    echo
  else
    echo "✔️  Pod UID $pod_uid ancora attivo. Nessuna azione."
  fi
done

echo "✅ Completato. Nessuna cartella è stata rimossa automaticamente."
