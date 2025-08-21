# Guacamole Remote Desktop Gateway

Apache Guacamole è un gateway di desktop remoto clientless che supporta protocolli standard come VNC, RDP e SSH.

## Installazione

### Metodo Automatico
```bash
./setup.sh
```

### Installazione Manuale

```bash
kubectl create namespace guacamole
helm repo add beryju https://charts.beryju.io
helm repo add bitnami https://charts.bitnami.com/bitnami

# Installa PostgreSQL
helm install postgresql bitnami/postgresql \
 --namespace guacamole \
 --set auth.username=guacamole \
 --set auth.password=password \
 --set auth.postgresPassword=password \
 --set auth.database=guacamole --wait

# Installa Guacamole
helm install guacamole beryju/guacamole \
 --namespace guacamole

# Inizializza database schema (necessario per correggere bug init-container)
kubectl run temp-init --image=guacamole/guacamole:1.6.0 --restart=Never -n guacamole --rm -i --tty -- /opt/guacamole/bin/initdb.sh --postgresql | kubectl exec -i postgresql-0 -n guacamole -- env PGPASSWORD=password psql -U guacamole -d guacamole

# Applica OAuth2 middleware e TLS secret
kubectl apply -f oauth2-middleware.yaml
kubectl get secret pindaroli-wildcard-tls -o yaml | sed 's/namespace: default/namespace: guacamole/' | grep -v resourceVersion | grep -v uid | grep -v creationTimestamp | kubectl apply -f -

# Applica Traefik IngressRoute
kubectl apply -f guacamole-ingress-route.yaml
```

## Accesso

- **URL**: https://guacamole.pindaroli.org
- **Autenticazione**: OAuth2 via Traefik middleware
- **Database**: PostgreSQL interno al cluster
- **Credenziali di default**: `guacadmin` / `guacadmin`

## Componenti

- **guacamole-guacamole**: Web interface (porta 80)
- **guacamole-guacd**: Guacamole daemon (porta 4822)
- **postgresql**: Database backend (porta 5432)

## Troubleshooting

### Init Container Error
Il chart BeryJu ha un bug nell'init container `loaddb` che causa errore:
```
psql: error: could not translate host name "-d" to address
```

**Soluzione**: Inizializzare manualmente lo schema con il comando fornito sopra.

### Database Schema
Lo schema include:
- Tabelle per users, connections, groups, permissions
- User di default `guacadmin` con tutti i privilegi sistema