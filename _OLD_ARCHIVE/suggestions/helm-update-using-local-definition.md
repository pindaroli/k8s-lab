# Helm Update Using Local Definition

## Update servarr with arr-values.yaml
```bash
helm upgrade servarr pindaroli/servarr -n arr -f servarr/arr-values.yaml
```

## Update servarr with oli-arr-values.yaml
```bash
helm upgrade servarr pindaroli/servarr -n arr -f servarr/oli-arr-values.yaml
```

## Test upgrade first (dry-run)
```bash
helm upgrade servarr pindaroli/servarr -n arr -f servarr/arr-values.yaml --debug --dry-run
```