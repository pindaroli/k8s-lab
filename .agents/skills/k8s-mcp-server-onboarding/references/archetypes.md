# Archetipi di Gestione Credenziali per Server MCP

Questo documento descrive i due archetipi codificati in [[mcp-secret-projection-pattern]] per garantire la compatibilità con l'immutabilità del filesystem (`readOnlyRootFilesystem: true`) imposta da ToolHive Operator.

---

## Matrice di Decisione

| Tipo di Credenziale | Esempi Tipici | Archetipo da Applicare | Meccanismo Tecnico |
| :--- | :--- | :---: | :--- |
| **Stringa Scalare** | API Key, Bearer Token, Password, Secret Key | **Archetipo 1** | ToolHive `spec.secrets` $\rightarrow$ Iniezione diretta in RAM (`process.env` / `os.environ`) |
| **File Strutturato / mTLS** | Kubeconfig, Talosconfig, Certificati X.509 (`.crt`/`.key`), Chiavi SSH | **Archetipo 2** | Volume Kubernetes Secret proiettato in sola lettura (`/etc/<app>/`) |

---

## Archetipo 1: Scalar Direct Injection (In-Memory)
- **Quando si usa**: quando il server MCP accetta credenziali passate come normali variabili d'ambiente (es. `OPNSENSE_API_KEY`, `GEMINI_API_KEY`).
- **Configurazione in `mcp-gateway-values.yaml`**:
  ```yaml
  toolhive:
    secrets:
      - name: <app>-mcp-credentials
        key: API_KEY
        targetEnvName: APP_API_KEY
  ```
- **Vantaggi**: Nessun filesystem toccato, memoria RAM isolata del processo, zero overhead di mount.

---

## Archetipo 2: Projected Secret Volume (File Strutturato)
- **Quando si usa**: quando i binari sottostanti (es. `talosctl`, `kubectl`, `ssh`) pretendono di leggere un file fisico di configurazione da disco.
- **Divieto Assoluto**: È tassativamente vietato iniettare il contenuto del file in una variabile d'ambiente (es. `CONFIG_DATA`) ed estrarlo all'avvio con script python (`with open('/tmp/config', 'w')`). Questo causa fallimenti di avvio o vulnerabilità sul filesystem immutabile.
- **Configurazione in `mcp-gateway-values.yaml`**:
  ```yaml
  toolhive:
    podTemplateSpec:
      spec:
        volumes:
          - name: config-vol
            secret:
              secretName: <app>-mcp-credentials
        containers:
          - name: mcp
            volumeMounts:
              - name: config-vol
                mountPath: /etc/<app>
                readOnly: true
    env:
      - name: APP_CONFIG_PATH
        value: "/etc/<app>/config.yaml"
  ```
- **Vantaggi**: Il secret viene materializzato dal Kubelet prima dell'avvio del container; il container può avviarsi in sola lettura assoluta (`readOnlyRootFilesystem: true`).
