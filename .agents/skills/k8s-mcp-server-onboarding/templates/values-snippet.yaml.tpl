  - name: <app>
    url: "http://mcp-<app>-mcp-proxy.mcp-system.svc.cluster.local:8080/mcp"
    hostname: "mcp-<app>-mcp-proxy.mcp-system.svc.cluster.local"
    enabled: true
    prefix: "<app>_"
    ingress:
      enabled: true
      host: "<app>-mcp-internal.pindaroli.org"
      port: 8080
    toolhive:
      enabled: true
      name: <app>-mcp
      image: ghcr.io/pindaroli/<app>-mcp:<app_version>
      transport: stdio
      proxyPort: 8080
      # [Opzionale] Per Archetipo 1 (Stringhe scalari in RAM):
      # secrets:
      #   - name: <app>-mcp-credentials
      #     key: API_KEY
      #     targetEnvName: APP_API_KEY
      # [Opzionale] Per Archetipo 2 (Projected Secret Volume):
      # podTemplateSpec:
      #   spec:
      #     volumes:
      #       - name: config-vol
      #         secret:
      #           secretName: <app>-mcp-credentials
      #     containers:
      #       - name: mcp
      #         volumeMounts:
      #           - name: config-vol
      #             mountPath: /etc/<app>
      #             readOnly: true
      env:
        - name: APP_ENV_SETTING
          value: "production"
      resources:
        limits:
          cpu: "300m"
          memory: "256Mi"
        requests:
          cpu: "50m"
          memory: "64Mi"
