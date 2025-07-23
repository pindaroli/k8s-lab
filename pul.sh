#!/bin/zsh

echo "🔍 Cerco PersistentVolume in stato Released..."
echo

released_pvs=($(kubectl get pv --no-headers | awk '$5 == "Released" {print $1}'))

if [[ $#released_pvs -eq 0 ]]; then
  echo "✅ Nessun PV in stato Released trovato. Niente da fare."
  exit 0
fi

for pv in $released_pvs; do
  echo "➡️  Trovato PV: $pv"
  kubectl get pv "$pv" -o custom-columns=NAME:.metadata.name,CAPACITY:.spec.capacity.storage,STATUS:.status.phase --no-headers
  
  vared -p "⚠️  Vuoi eliminare questo PV? [y/N]: " -c confirm

  if [[ "$confirm" == "y" || "$confirm" == "Y" ]]; then
    echo "🗑️  Elimino $pv ..."
    kubectl delete pv "$pv"
  else
    echo "⏩  Skip $pv"
  fi

  echo
done

echo "✅ Operazione completata."
