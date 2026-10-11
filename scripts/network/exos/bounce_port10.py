#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Script di ripristino idempotente SerDes SFP+ Porta 10 per ExtremeXOS
# Se l'interfaccia e' gia' 'active', evita qualsiasi operazione e termina.
# Solo se la porta e' down o in stallo 'ready', esegue il recovery bounce.
import sys
import time
import exsh

# 1. Attesa iniziale prudenziale (15s) per dare tempo al PHY rame di allinearsi
time.sleep(15)

# 2. Controllo dello stato del link della porta 10
status = exsh.clicmd("show ports 10 information", True)

# 3. Idempotenza: se il link e' gia' attivo e funzionante, esci senza fare nulla
if "active" in status.lower():
    sys.exit(0)

# 4. Solo se la porta NON e' attiva, esegui il recovery bounce
exsh.clicmd("disable ports 10")
time.sleep(2)
exsh.clicmd("enable ports 10")
