#!/bin/bash
# scripts/check_qbittorrent_net.sh
# Diagnostic script for qBittorrent "firewalled" status

export KUBECONFIG=talos-config/kubeconfig

echo "🔍 [1/4] Verifica Stato Pod qBittorrent..."
POD_NAME=$(kubectl get pods -n arr -l app.kubernetes.io/name=qbittorrent -o name)
kubectl get $POD_NAME -n arr

echo -e "\n🌐 [2/4] Verifica Servizio LoadBalancer (MetalLB)..."
SVC_INFO=$(kubectl get svc servarr-qbittorrent-bt -n arr -o json)
LB_IP=$(echo $SVC_INFO | python3 -c "import json,sys; print(json.load(sys.stdin)['status']['loadBalancer']['ingress'][0]['ip'])")
BT_PORT=$(echo $SVC_INFO | python3 -c "import json,sys; print(json.load(sys.stdin)['spec']['ports'][0]['port'])")

echo "IP MetalLB: $LB_IP"
echo "Porta BitTorrent: $BT_PORT"

echo -e "\n🛠️ [3/4] Verifica porta interna al Pod (deve corrispondere alla porta nel WebUI)..."
# Cerchiamo di capire che porta qBittorrent pensa di usare
kubectl exec -n arr $POD_NAME -- netstat -tulpn | grep qbit || echo "Netstat non disponibile, provo a leggere i log..."
kubectl logs -n arr $POD_NAME | grep -i "listening on" | tail -n 1

echo -e "\n📡 [4/4] Test connettività locale (Mac Studio -> Cluster)..."
nc -zv -w 2 $LB_IP $BT_PORT && echo "✅ Porta raggiungibile internamente!" || echo "❌ Porta CHIUSA internamente!"

echo -e "\n--------------------------------------------------"
echo "📢 DIAGNOSI VELOCE:"
echo "1. Se il test [4/4] è PASSATO ma qbit è ancora 'firewalled':"
echo "   -> Vai su OPNsense e crea una regola NAT: WAN (qualsiasi porta) -> $LB_IP:$BT_PORT"
echo "2. Se il test [4/4] è FALLITO:"
echo "   -> Verifica che dentro qBittorrent (Opzioni -> Connessione) la porta sia impostata su $BT_PORT"
echo "--------------------------------------------------"
