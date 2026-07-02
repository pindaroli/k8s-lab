#!/bin/bash
# scripts/security/check_certificate.sh
# Diagnostic script to check SSL certificates, secrets, and Traefik synchronization.

set -euo pipefail

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== SSL/TLS Certificate Diagnostic Report ===${NC}\n"

# 1. Controllo Certificati in Kubernetes
echo -e "${BLUE}[1/4] Controllo stato dei Certificati in Kubernetes...${NC}"
if ! kubectl get certificates -A >/dev/null 2>&1; then
    echo -e "${RED}❌ Impossibile comunicare con il cluster Kubernetes o CRD Certificate non trovato.${NC}"
    exit 1
fi

kubectl get certificate -A -o custom-columns="NAMESPACE:.metadata.namespace,NAME:.metadata.name,READY:.status.conditions[?(@.type=='Ready')].status,NOT_AFTER:.status.notAfter,SECRET:.spec.secretName"
echo ""

# 2. Controllo validità dei Secret
echo -e "${BLUE}[2/4] Controllo date dei certificati salvati nei Secret...${NC}"
namespaces=("traefik" "arr" "default")
secret_name="pindaroli-wildcard-tls"

# Stringa per accumulare le date di scadenza valide trovate nei secret
valid_expirations=""

for ns in "${namespaces[@]}"; do
    if kubectl get secret -n "$ns" "$secret_name" >/dev/null 2>&1; then
        # Estrai date usando openssl
        dates=$(kubectl get secret -n "$ns" "$secret_name" -o jsonpath='{.data.tls\.crt}' | base64 -d | openssl x509 -noout -dates 2>/dev/null)
        not_before=$(echo "$dates" | grep "notBefore=" | cut -d= -f2)
        not_after=$(echo "$dates" | grep "notAfter=" | cut -d= -f2)

        # Accumula la scadenza per il confronto successivo
        valid_expirations="${valid_expirations}|${not_after}"

        # Verifica se è scaduto
        if openssl x509 -noout -checkend 0 -in <(kubectl get secret -n "$ns" "$secret_name" -o jsonpath='{.data.tls\.crt}' | base64 -d) >/dev/null 2>&1; then
            echo -e "  - Secret ${GREEN}${ns}/${secret_name}${NC}: Valido (Scade il: ${GREEN}${not_after}${NC})"
        else
            echo -e "  - Secret ${RED}${ns}/${secret_name}${NC}: ${RED}SCADUTO o NON VALIDO${NC} (Scade il: ${not_after})"
        fi
    else
        echo -e "  - Secret ${YELLOW}${ns}/${secret_name}${NC}: Non trovato"
    fi
done
echo ""

# 3. Controllo allineamento dei Pod di Traefik rispetto all'ultimo update del Secret
echo -e "${BLUE}[3/4] Verifica allineamento dei pod di Traefik...${NC}"
# Recupera l'ultimo tempo di modifica del secret in traefik
secret_update_raw=$(kubectl get secret -n traefik "$secret_name" -o jsonpath='{.metadata.managedFields[?(@.manager=="cert-manager-certificates-issuing")].time}' 2>/dev/null || true)
if [ -z "$secret_update_raw" ]; then
    secret_update_raw=$(kubectl get secret -n traefik "$secret_name" -o jsonpath='{.metadata.managedFields[0].time}' 2>/dev/null || true)
fi

if [ -n "$secret_update_raw" ]; then
    # Converte timestamp in epoch
    secret_epoch=$(date -j -f "%Y-%m-%dT%H:%M:%SZ" "$secret_update_raw" "+%s" 2>/dev/null || date -d "$secret_update_raw" "+%s" 2>/dev/null || echo 0)
    echo -e "  Ultimo aggiornamento Secret in traefik: ${YELLOW}${secret_update_raw}${NC}"

    # Recupera i pod di Traefik
    pods_info=$(kubectl get pods -n traefik -l app.kubernetes.io/name=traefik -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.startTime}{"\n"}{end}')

    need_restart=false
    while read -r pod_name pod_start_raw; do
        if [ -n "$pod_name" ]; then
            pod_epoch=$(date -j -f "%Y-%m-%dT%H:%M:%SZ" "$pod_start_raw" "+%s" 2>/dev/null || date -d "$pod_start_raw" "+%s" 2>/dev/null || echo 0)

            if [ "$pod_epoch" -lt "$secret_epoch" ]; then
                echo -e "  - Pod ${YELLOW}${pod_name}${NC}: Avviato il ${pod_start_raw} (${RED}Prima dell'aggiornamento del secret${NC})"
                need_restart=true
            else
                echo -e "  - Pod ${GREEN}${pod_name}${NC}: Avviato il ${pod_start_raw} (${GREEN}Dopo l'aggiornamento del secret${NC})"
            fi
        fi
    done <<< "$pods_info"

    if [ "$need_restart" = true ]; then
        echo -e "\n${YELLOW}⚠️ Attenzione: Uno o più pod di Traefik sono stati avviati prima del rinnovo del certificato.${NC}"
        echo -e "Si raccomanda di riavviare Traefik con:"
        echo -e "  ${BLUE}kubectl rollout restart daemonset/traefik -n traefik${NC}"
    else
        echo -e "\n${GREEN}✅ Tutti i pod di Traefik sono stati avviati dopo l'aggiornamento del secret.${NC}"
    fi
else
    echo -e "  ${RED}Impossibile determinare la data di aggiornamento del Secret.${NC}"
fi
echo ""

# 4. Verifica certificato servito via rete
echo -e "${BLUE}[4/4] Verifica certificato servito via rete (Split-Horizon)...${NC}"
test_host="home-internal.pindaroli.org"
echo -e "  Connessione a ${test_host}..."

# Esegue handshake TLS
live_cert_info=$(echo | openssl s_client -connect "${test_host}:443" -servername "${test_host}" 2>/dev/null | openssl x509 -noout -dates 2>/dev/null || true)

if [ -n "$live_cert_info" ]; then
    live_not_after=$(echo "$live_cert_info" | grep "notAfter=" | cut -d= -f2)
    live_not_before=$(echo "$live_cert_info" | grep "notBefore=" | cut -d= -f2)
    echo -e "  - Certificato live servito: Valido da ${GREEN}${live_not_before}${NC} a ${GREEN}${live_not_after}${NC}"

    # Controlla se la data di scadenza coincide con uno qualsiasi dei secret validi trovati
    if [[ "$valid_expirations" == *"$live_not_after"* ]]; then
        echo -e "  - Allineamento Rete-Secret: ${GREEN}Allineato ✅${NC} (Traefik sta servendo un certificato aggiornato corrispondente a uno dei namespace)"
    else
        echo -e "  - Allineamento Rete-Secret: ${RED}DISALLINEATO ❌${NC} (Traefik sta ancora servendo un certificato non aggiornato o non corrispondente ai secret del cluster)"
    fi
else
    echo -e "  ${RED}Impossibile connettersi a ${test_host} su porta 443 per verificare il certificato.${NC}"
fi

echo -e "\n${BLUE}===============================================${NC}"
