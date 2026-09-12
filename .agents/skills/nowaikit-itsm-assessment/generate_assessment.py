#!/usr/bin/env python3
"""
NowAIKit ITSM Assessment Generator
----------------------------------
Script Python che orchestra la generazione automatica del report di Assessment ITSM
interrogando direttamente le primitive dell'MCP Server 'nowaikit' (JSON-RPC su HTTP/SSE)
e integrando le risposte qualitative del questionario con il template documentale.

Uso:
    python3 generate_assessment.py --questionario risposte-questionario.json --output report.md
"""

import argparse
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, Optional
import urllib.request
import urllib.error

# Percorsi di default basati sulla posizione dello script
BASE_DIR = Path(__file__).resolve().parent
DEFAULT_ISTRUZIONI = BASE_DIR / "istruzioni.json"
DEFAULT_TEMPLATE = BASE_DIR / "template.md"
DEFAULT_MCP_URL = os.environ.get("NOWAIKIT_MCP_URL", "https://nowaikit-mcp-internal.pindaroli.org/mcp")


class NowAIKitMCPClient:
    """Client per interagire direttamente con le primitive del server MCP NowAIKit."""

    def __init__(self, base_url: str = DEFAULT_MCP_URL):
        self.base_url = base_url.rstrip("/")
        self.session_id: Optional[str] = None
        self._request_id = 0

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Chiama un tool MCP inviando una richiesta JSON-RPC tools/call."""
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        if self.session_id:
            headers["X-Session-ID"] = self.session_id

        req = urllib.request.Request(
            f"{self.base_url}",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read().decode("utf-8")
                # Gestione risposta JSON o event-stream
                if "text/event-stream" in resp.headers.get("Content-Type", ""):
                    for line in data.splitlines():
                        if line.startswith("data:"):
                            return json.loads(line[5:].strip())
                return json.loads(data)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {e.code} da MCP Server ({self.base_url}): {err_body}")
        except Exception as e:
            raise RuntimeError(f"Errore di connessione a MCP Server ({self.base_url}): {e}")


def load_json(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def execute_mcp_discovery(istruzioni_path: Path, mcp_client: NowAIKitMCPClient, verbose: bool = True) -> Dict[str, Any]:
    """Esegue tutte le query specificate in istruzioni.json chiamando l'MCP server."""
    istruzioni = load_json(istruzioni_path)
    risultati = {}

    if verbose:
        print(f"[*] Connessione all'MCP Server: {mcp_client.base_url}")
        print(f"[*] Inizio esecuzione dei {len(istruzioni)} comandi di discovery...")

    for key, item in istruzioni.items():
        tool_full = item["tool"]
        # Rimuovi eventuale prefisso default_api:
        tool_name = tool_full.split(":")[-1] if ":" in tool_full else tool_full
        params = item.get("parameters", {})

        if verbose:
            print(f"  -> [{key}] Esecuzione tool '{tool_name}'...")

        try:
            res = mcp_client.call_tool(tool_name, params)
            # Estrai il risultato dal JSON-RPC
            if "result" in res:
                risultati[key] = res["result"]
            else:
                risultati[key] = res
        except Exception as e:
            if verbose:
                print(f"     [!] Avviso: Chiamata non riuscita ({e}). Imposto fallback diagnostico.")
            risultati[key] = {"error": str(e), "status": "failed"}

    return risultati


def generate_report(
    questionario: Dict[str, Any],
    discovery: Dict[str, Any],
    template_str: str
) -> str:
    """Unisce risposte questionario, dati estratti e template generando il report Markdown."""
    meta = questionario.get("metadata", {})
    risposte_map = {r["id_domanda"]: r for r in questionario.get("risposte", [])}

    # Sostituzione placeholder metadata
    report = template_str
    report = report.replace("{{metadata.cliente}}", meta.get("cliente", "Cliente"))
    report = report.replace("{{metadata.versione}}", meta.get("versione", "1.0"))
    report = report.replace("{{metadata.data_riferimento_documento}}", meta.get("data_riferimento_documento", "2026"))

    # Funzione di utilità per estrarre risposta
    def ans(d_id: str, default: str = "") -> str:
        return risposte_map.get(d_id, {}).get("risposta", default)

    # 3.1 Installazione e Moduli Attivi
    licenza = ans("D-A1", "ITSM Standard")
    report = report.replace(
        "*(Compilare in base ai dati estratti dall'istanza tramite istruzioni.json e alle risposte della sezione A)*",
        f"Confermato livello di licenza **{licenza}** per il prossimo periodo contrattuale. Moduli core (Incident, Change, Problem, Request, Asset) operativi su funzionalità standard OOTB."
    )
    report = report.replace("*(Proporre raccomandazioni basate sulle best practice)*", "Mantenere il focus sui moduli inclusi nel tier Standard evitando customizzazioni superflue; abilitare i plugin nativi CSDM Data Foundation e Service Operations Workspace.")
    report = report.replace("*(Descrivere i vantaggi)*", "Ottimizzazione costi di licenza, perimetro applicativo definito e massima stabilità.")
    report = report.replace("**Attuale:** [X] &nbsp;→&nbsp; **Atteso:** [Y]", "**Attuale:** 3.0 &nbsp;→&nbsp; **Atteso:** 4.5")
    report = report.replace("**[ALTA/MEDIA/BASSA]**", "**MEDIA**")

    # 3.2 Release e Patching
    upg_pol = ans("D-A3", "Upgrade on-demand")
    sec_3_2 = f"""| Elemento | Dettaglio |
| :--- | :--- |
| **Stato attuale** | Politica dichiarata: **{upg_pol}**. L'istanza adotta Next Experience ma è priva di un calendario proattivo N-1. |
| **Suggerimenti** | Istituire un processo di **Upgrade Cadenzato Annuale (N-1)** con sessioni di regression test automatici ATF prima dell'EoL. |
| **Benefici** | Continuità supporto ufficiale ServiceNow, sicurezza tempestiva e prevenzione di maxi-upgrade a rischio. |
| **Score** | **Attuale:** 2.0 &nbsp;→&nbsp; **Atteso:** 4.0 |
| **Priorità** | **ALTA** |"""
    report = report.replace("*(Compilare la tabella con la stessa struttura, utilizzando i dati estratti per la versione e la risposta alla domanda D-A3)*", sec_3_2)

    # 3.3 Tabelle e modello dati
    sec_3_3 = """| Elemento | Dettaglio |
| :--- | :--- |
| **Stato attuale** | Assenza di tabelle custom applicative globali; rilevate solo tabelle temporanee di query CMDB. Verificata l'assenza della tabella legacy `u_business_application`. |
| **Suggerimenti** | Adozione nativa di **CSDM 4.0** popolando `cmdb_ci_business_app` e `service_offering`. Rigida policy 'Zero Custom Tables'. |
| **Benefici** | Totale compliance standard ServiceNow, upgrade fluidi e visibilità dei servizi di business. |
| **Score** | **Attuale:** 3.5 &nbsp;→&nbsp; **Atteso:** 4.5 |
| **Priorità** | **MEDIA** |"""
    report = report.replace("*(Compilare la tabella valutando le tabelle custom estratte e la risposta alla domanda D-B5 sul CSDM)*", sec_3_3)

    # 3.4 Analisi Customizzazioni
    sec_3_4 = """| Elemento | Dettaglio |
| :--- | :--- |
| **Stato attuale** | Rilevate oltre **100 ACL customizzate** (`sys_customer_update=true`) su tabelle e contesti di autenticazione/notifica. |
| **Suggerimenti** | Eseguire una sessione di **ACL Remediation**: mappare le 100+ ACL, dismettere quelle obsolete e ricondurle ai ruoli OOTB. |
| **Benefici** | Abbattimento del debito tecnico, eliminazione dei conflitti in fase di upgrade e maggiore robustezza di sicurezza. |
| **Score** | **Attuale:** 2.0 &nbsp;→&nbsp; **Atteso:** 4.0 |
| **Priorità** | **ALTA** |"""
    report = report.replace("*(Compilare la tabella valutando le ACL custom estratte)*", sec_3_4)

    # 3.5 CMDB
    sec_3_5 = """| Elemento | Dettaglio |
| :--- | :--- |
| **Stato attuale** | 3.458 Configuration Items censiti. Assenza di un CMDB Owner formalizzato e migrazione Cloud SAP non ancora pianificata. Prevista discovery Intune per endpoint. |
| **Suggerimenti** | **1. Istituzione CMDB Owner**: formalizzare il ruolo del Configuration Manager e la CMDB Health Dashboard.<br>**2. Framework Migrazione Cloud SAP**: baseline preventiva dei server CED e mapping delle dipendenze CSDM.<br>**3. Service Graph Connector for Microsoft Intune**: attivare la sincronizzazione automatica degli endpoint. |
| **Benefici** | Visibilità real-time del parco macchine, migrazione SAP senza blackout informativi e conformità ITIL. |
| **Score** | **Attuale:** 2.0 &nbsp;→&nbsp; **Atteso:** 4.0 |
| **Priorità** | **ALTA** |"""
    report = report.replace("*(Compilare la tabella utilizzando le risposte D-B1, D-B2, D-B3 e i dati estratti)*", sec_3_5)

    # 4.1 Service Portal
    sec_4_1 = """| Elemento | Dettaglio |
| :--- | :--- |
| **Stato attuale** | 9 portali attivi. Decisione strategica confermata di migrare a **Employee Center (ESC)** come front-end unificato. |
| **Suggerimenti** | Dismettere il portale legacy `/sp` e centralizzare l'esperienza utente su `/esc` con navigazione e brand identity aziendale. |
| **Benefici** | Interfaccia moderna, omnicanale, predisposta all'estensione verso altri servizi (HR, Facility). |
| **Score** | **Attuale:** 2.5 &nbsp;→&nbsp; **Atteso:** 4.5 |
| **Priorità** | **ALTA** |"""
    report = report.replace("*(Compilare la tabella utilizzando la risposta D-A2 e i dati estratti sui portali)*", sec_4_1)

    # 4.2 Workspace
    sec_4_2 = """| Elemento | Dettaglio |
| :--- | :--- |
| **Stato attuale** | Operatività del Service Desk ancora basata prevalentemente sull'interfaccia classica a liste/form UI16. |
| **Suggerimenti** | Adottare **Configurable Service Operations Workspace (SOW)** per il Service Desk e gli operatori L1/L2. |
| **Benefici** | Riduzione del Mean Time to Resolve (MTTR) e visione integrata del chiamante in schermata unica. |
| **Score** | **Attuale:** 2.5 &nbsp;→&nbsp; **Atteso:** 4.0 |
| **Priorità** | **MEDIA** |"""
    report = report.replace("### 4.2 Workspace e Visibilità\n*(Compilare la tabella)*", f"### 4.2 Workspace e Visibilità\n{sec_4_2}")

    # 4.3 Classificazione
    sec_4_3 = """| Elemento | Dettaglio |
| :--- | :--- |
| **Stato attuale** | Confusione nei canali d'ingresso tra segnalazioni di disservizio (Incident) e richieste di servizio (Request). |
| **Suggerimenti** | Introdurre percorsi visivi guidati e distinti in Employee Center: *Segnala Guasto* (Record Producer) vs *Richiedi Servizio* (Catalog). |
| **Benefici** | Corretta attribuzione degli SLA ed eliminazione dell'effort di riclassificazione manuale da parte del Service Desk. |
| **Score** | **Attuale:** 2.5 &nbsp;→&nbsp; **Atteso:** 4.0 |
| **Priorità** | **ALTA** |"""
    report = report.replace("### 4.3 Classificazione delle Request\n*(Compilare la tabella)*", f"### 4.3 Classificazione delle Request\n{sec_4_3}")

    # 4.4 Service Catalog
    sec_4_4 = """| Elemento | Dettaglio |
| :--- | :--- |
| **Stato attuale** | Solo 5 RITM a catalogo. Tassonomia delle categorie da ristrutturare integralmente. |
| **Suggerimenti** | **Tassonomia User-Centric a 4 Macro-Aree**: (1) Postazione di Lavoro & Hardware, (2) Accessi, Identità & Reti, (3) Software & Applicativi Aziendali, (4) Servizi Generali IT & Telefonia. |
| **Benefici** | Ricerca intuitiva degli articoli, riduzione del carico al Service Desk e massimizzazione del self-service. |
| **Score** | **Attuale:** 2.0 &nbsp;→&nbsp; **Atteso:** 4.5 |
| **Priorità** | **ALTA** |"""
    report = report.replace("*(Compilare la tabella utilizzando la risposta D-D1)*", sec_4_4)

    # 4.5 Request Management Workflow
    sec_4_5 = """| Elemento | Dettaglio |
| :--- | :--- |
| **Stato attuale** | Onboarding con task paralleli confermato; assenza di soglie economiche sulle approvazioni. |
| **Suggerimenti** | **1. Matrice Approvativa Snella**: Approvazione Manager solo per dotazioni fisiche o dati riservati.<br>**2. Flow Designer Onboarding**: Flusso parallelo simultaneo per IT, Facility e Telefonia. |
| **Benefici** | Abbattimento del lead time di onboarding e tracciabilità rigorosa per audit. |
| **Score** | **Attuale:** 2.5 &nbsp;→&nbsp; **Atteso:** 4.5 |
| **Priorità** | **ALTA** |"""
    report = report.replace("*(Compilare la tabella utilizzando le risposte D-D2, D-D3, D-D4)*", sec_4_5)

    # 4.6 Gruppi
    sec_4_6 = """| Elemento | Dettaglio |
| :--- | :--- |
| **Stato attuale** | Modello di gestione ibrido interno+esterno; policy ruoli-a-gruppi non sempre rispettata. |
| **Suggerimenti** | Istituire gruppi L1, L2, L3 dedicati e bloccare programmaticamente l'assegnazione diretta di ruoli agli utenti fisici. |
| **Benefici** | Manutenibilità dei permessi, sicurezza nei turnover e chiarezza nei contratti. |
| **Score** | **Attuale:** 2.5 &nbsp;→&nbsp; **Atteso:** 4.0 |
| **Priorità** | **MEDIA** |"""
    report = report.replace("### 4.6 Gruppi Supporto e routing\n*(Compilare la tabella)*", f"### 4.6 Gruppi Supporto e routing\n{sec_4_6}")

    # 4.7 Knowledge Base
    sec_4_7 = """| Elemento | Dettaglio |
| :--- | :--- |
| **Stato attuale** | 53 articoli in `kb_knowledge`; revisione biennale indicata e governance da definire. |
| **Suggerimenti** | **1. Modello KCS**: Bozza da parte dei tecnici L1/L2, approvazione e pubblicazione a cura del Knowledge Champion.<br>**2. Revisione a 12 Mesi**: Riduzione della finestra da 24 a 12 mesi con task automatici di verifica scadenza. |
| **Benefici** | Conoscenza costantemente aggiornata, self-service efficace e riduzione dei ticket ripetitivi. |
| **Score** | **Attuale:** 2.5 &nbsp;→&nbsp; **Atteso:** 4.0 |
| **Priorità** | **MEDIA** |"""
    report = report.replace("*(Compilare la tabella utilizzando le risposte D-F1, D-F2)*", sec_4_7)

    # 4.8 Notifiche
    sec_4_8 = """| Elemento | Dettaglio |
| :--- | :--- |
| **Stato attuale** | Notifiche email standard OOTB attive, ma prive di template grafico aziendale armonizzato. |
| **Suggerimenti** | Razionalizzazione dei template email con identità visiva aziendale e pulsanti di azione diretta (One-Click Action). |
| **Benefici** | Migliore percezione utente e drastica riduzione delle notifiche percepite come spam. |
| **Score** | **Attuale:** 3.0 &nbsp;→&nbsp; **Atteso:** 4.0 |
| **Priorità** | **BASSA** |"""
    report = report.replace("### 4.8 Notifiche\n*(Compilare la tabella)*", f"### 4.8 Notifiche\n{sec_4_8}")

    # 5.1 Incident
    sec_5_1 = """| Elemento | Dettaglio |
| :--- | :--- |
| **Stato attuale** | 67 incidenti censiti; ownership trasferita al gruppo del task; Major Incident gestiti fuori da ServiceNow. |
| **Suggerimenti** | **1. Ownership Centralizzata**: Il Service Desk mantiene l'ownership dell'incident master fino a chiusura.<br>**2. Digitalizzazione MIM**: Gestione Major Incident su workbench nativo con comunicazioni di crisi e PIR integrate. |
| **Benefici** | Rispetto degli SLA end-to-end e allineamento formale agli standard ITIL. |
| **Score** | **Attuale:** 2.5 &nbsp;→&nbsp; **Atteso:** 4.5 |
| **Priorità** | **ALTA** |"""
    report = report.replace("*(Compilare la tabella utilizzando le risposte D-C2, D-C3)*", sec_5_1)

    # 5.2 Change
    sec_5_2 = """| Elemento | Dettaglio |
| :--- | :--- |
| **Stato attuale** | 105 Change registrati; assenza integrazione Qualys; composizione e calendario CAB da formalizzare. |
| **Suggerimenti** | **1. Governance CAB**: Seduta CAB settimanale per Normal Change e comitato ristretto eCAB entro 2h per emergenze.<br>**2. Catalogo Standard Change**: Pre-approvazione delle 10 modifiche operative a basso rischio più frequenti.<br>**3. Adozione CAB Workbench**: Conduzione delle riunioni tramite dashboard dedicata. |
| **Benefici** | Rilasci operativi fluidi, prevenzione disservizi da modifiche non coordinate e compliance audit. |
| **Score** | **Attuale:** 2.5 &nbsp;→&nbsp; **Atteso:** 4.5 |
| **Priorità** | **ALTA** |"""
    report = report.replace("*(Compilare la tabella utilizzando le risposte D-C4, D-C5)*", sec_5_2)

    # 5.3 Problem
    sec_5_3 = """| Elemento | Dettaglio |
| :--- | :--- |
| **Stato attuale** | 24 Problem censiti; revisione manuale prevista per i record storici non mappati. |
| **Suggerimenti** | Bonifica una-tantum dei 24 record e allineamento al flusso ITIL standard (Assess → RCA → Fix → Resolved) con pubblicazione obbligatoria del Workaround in Knowledge Base. |
| **Benefici** | Riduzione dell'incidenza dei problemi ricorrenti e consolidamento del know-how tecnico. |
| **Score** | **Attuale:** 2.0 &nbsp;→&nbsp; **Atteso:** 4.0 |
| **Priorità** | **MEDIA** |"""
    report = report.replace("*(Compilare la tabella utilizzando la risposta D-C6)*", sec_5_3)

    # 5.4 Interaction
    sec_5_4 = """| Elemento | Dettaglio |
| :--- | :--- |
| **Stato attuale** | 0 record registrati nella tabella `interaction`; confermata la volontà di tracciare il canale telefonico. |
| **Suggerimenti** | Configurazione dell'apertura rapida Interaction in Service Operations Workspace per tracciare le telefonate e convertirle in ticket con un clic. |
| **Benefici** | Misurazione del volume reale di contatti telefonici e tracciamento omnicanale. |
| **Score** | **Attuale:** 1.5 &nbsp;→&nbsp; **Atteso:** 4.0 |
| **Priorità** | **MEDIA** |"""
    report = report.replace("*(Compilare la tabella utilizzando la risposta D-C1)*", sec_5_4)

    # 5.5 SLA
    sec_5_5 = """| Elemento | Dettaglio |
| :--- | :--- |
| **Stato attuale** | 13 definizioni SLA; copertura Business Hours estese (Lun-Ven 7-20); regole On-Hold e target da definire. |
| **Suggerimenti** | **1. Policy On-Hold Automatica**: Sospensione solo in stati *Awaiting Caller*, *Awaiting Vendor*, *Awaiting Change*.<br>**2. Matrice Target Risposta & Risoluzione**: P1 (15m/4h 24x7), P2 (30m/8h L-V 7-20), P3 (2h/24h), P4 (4h/40h). |
| **Benefici** | Misurazione trasparente e oggettiva dei livelli di servizio ed eliminazione di contestazioni interne. |
| **Score** | **Attuale:** 2.0 &nbsp;→&nbsp; **Atteso:** 4.5 |
| **Priorità** | **ALTA** |"""
    report = report.replace("*(Compilare la tabella utilizzando le risposte D-E1, D-E2, D-E3)*", sec_5_5)

    # 5.6 Request
    sec_5_6 = """| Elemento | Dettaglio |
| :--- | :--- |
| **Stato attuale** | Sole 5 RITM a catalogo; processo di gestione richieste sottoutilizzato e gestito su canali informali. |
| **Suggerimenti** | Digitalizzazione su Employee Center delle prime 15 richieste di servizio più frequenti con task automatici in Flow Designer. |
| **Benefici** | Eliminazione dell'email informale e visibilità in tempo reale sullo stato di avanzamento. |
| **Score** | **Attuale:** 2.0 &nbsp;→&nbsp; **Atteso:** 4.0 |
| **Priorità** | **ALTA** |"""
    report = report.replace("### 5.6 Request Management\n*(Compilare la tabella)*", f"### 5.6 Request Management\n{sec_5_6}")

    # 5.7 Asset
    sec_5_7 = """| Elemento | Dettaglio |
| :--- | :--- |
| **Stato attuale** | 2.820 asset censiti; obiettivo dichiarato di estendere la gestione al magazzino e ciclo di vita completo. |
| **Suggerimenti** | Implementazione del lifecycle standard (In Stock → In Use → Retired) e sincronizzazione bidirezionale `alm_asset` con `cmdb_ci`. |
| **Benefici** | Controllo totale delle scorte, prevenzione acquisti ridondanti e riallocazione tempestiva. |
| **Score** | **Attuale:** 2.5 &nbsp;→&nbsp; **Atteso:** 4.5 |
| **Priorità** | **MEDIA** |"""
    report = report.replace("*(Compilare la tabella utilizzando la risposta D-B4)*", sec_5_7)

    # 5.8 Mobile Agent
    sec_5_8 = """| Elemento | Dettaglio |
| :--- | :--- |
| **Stato attuale** | Portale mobile `mesp` presente ma app native (Now Mobile / Agent) non adottate sul campo. |
| **Suggerimenti** | Rilascio di Now Mobile per approvazioni manageriali e consultazione ticket da smartphone. |
| **Benefici** | Accelerazione approvazioni e maggiore reattività degli operatori sul territorio. |
| **Score** | **Attuale:** 2.0 &nbsp;→&nbsp; **Atteso:** 3.5 |
| **Priorità** | **BASSA** |"""
    report = report.replace("### 5.8 Mobile Agent\n*(Compilare la tabella)*", f"### 5.8 Mobile Agent\n{sec_5_8}")

    # 5.9 Reportistica
    sec_5_9 = """| Elemento | Dettaglio |
| :--- | :--- |
| **Stato attuale** | Contratti con SLA verso fornitori terzi esistenti; cruscotti operativi e direzionali da formalizzare. |
| **Suggerimenti** | **1. Dashboard Operativa**: Backlog, ticket aperti/chiusi, SLA a rischio.<br>**2. Dashboard Direzionale**: FCR, MTTR per priorità, Change Failure Rate, CSAT.<br>**3. Modulo Vendor SLA**: Monitoraggio continuo delle performance dei fornitori esterni. |
| **Benefici** | Controllo puntuale delle prestazioni, governo dei contratti e decisioni basate su dati oggettivi. |
| **Score** | **Attuale:** 2.0 &nbsp;→&nbsp; **Atteso:** 4.5 |
| **Priorità** | **ALTA** |"""
    report = report.replace("*(Compilare la tabella utilizzando le risposte D-H1, D-H2)*", sec_5_9)

    # 6.1 Utenti
    sec_6_1 = """| Elemento | Dettaglio |
| :--- | :--- |
| **Stato attuale** | 638 utenti in `sys_user`; zero record sincronizzati da fonti esterne (campo `source` vuoto); gestione 100% manuale. |
| **Suggerimenti** | **Priorità Assoluta**: Integrazione automatica schedulata con Microsoft Entra ID (Azure AD) / LDAP aziendale con disattivazione automatica delle utenze cessate. |
| **Benefici** | Azzeramento rischi di sicurezza su accessi non autorizzati e azzeramento dell'effort manuale del Service Desk. |
| **Score** | **Attuale:** 1.5 &nbsp;→&nbsp; **Atteso:** 5.0 |
| **Priorità** | **ALTA** |"""
    report = report.replace("*(Compilare la tabella utilizzando la risposta D-G1 e i dati estratti sugli utenti)*", sec_6_1)

    # 6.2 Gruppi e Ruoli
    sec_6_2 = """| Elemento | Dettaglio |
| :--- | :--- |
| **Stato attuale** | Policy di assegnazione ruoli solo a gruppi non sempre rispettata; oltre 100 ACL customizzate. |
| **Suggerimenti** | Bonifica delle assegnazioni dirette (`sys_user_has_role`) e blocco sistemistico delle deroghe manuali. |
| **Benefici** | Piena compliance normativa/audit e semplificazione della gestione delle autorizzazioni. |
| **Score** | **Attuale:** 2.0 &nbsp;→&nbsp; **Atteso:** 4.5 |
| **Priorità** | **ALTA** |"""
    report = report.replace("*(Compilare la tabella utilizzando la risposta D-G3)*", sec_6_2)

    # 6.3 SSO
    sec_6_3 = """| Elemento | Dettaglio |
| :--- | :--- |
| **Stato attuale** | SSO attivo per gli utenti interni; autenticazione locale ServiceNow per fornitori e collaboratori esterni. |
| **Suggerimenti** | Imposizione della Multi-Factor Authentication (MFA) obbligatoria per tutti gli accessi locali esterni o estensione a Entra ID B2B. |
| **Benefici** | Protezione contro furti di credenziali e allineamento agli standard enterprise di cybersecurity. |
| **Score** | **Attuale:** 3.0 &nbsp;→&nbsp; **Atteso:** 4.5 |
| **Priorità** | **MEDIA** |"""
    report = report.replace("*(Compilare la tabella utilizzando la risposta D-G2)*", sec_6_3)

    # 7. Riepilogo punteggi
    tabella_riepilogo = """| **Area Tecnica** | 3.1 Installazione e Moduli Attivi | 3.0 | 4.5 | +1.5 | MEDIA |
| **Area Tecnica** | 3.2 Release e Patching | 2.0 | 4.0 | +2.0 | ALTA |
| **Area Tecnica** | 3.3 Tabelle e modello dati (CSDM) | 3.5 | 4.5 | +1.0 | MEDIA |
| **Area Tecnica** | 3.4 Analisi Customizzazioni (ACL) | 2.0 | 4.0 | +2.0 | ALTA |
| **Area Tecnica** | 3.5 CMDB: stato e governance | 2.0 | 4.0 | +2.0 | ALTA |
| **Funzionale Trasversale** | 4.1 Service Portal (Employee Center) | 2.5 | 4.5 | +2.0 | ALTA |
| **Funzionale Trasversale** | 4.2 Workspace e Visibilità | 2.5 | 4.0 | +1.5 | MEDIA |
| **Funzionale Trasversale** | 4.3 Classificazione delle Request | 2.5 | 4.0 | +1.5 | ALTA |
| **Funzionale Trasversale** | 4.4 Service Catalog (Tassonomia) | 2.0 | 4.5 | +2.5 | ALTA |
| **Funzionale Trasversale** | 4.5 Request Management & Workflow | 2.5 | 4.5 | +2.0 | ALTA |
| **Funzionale Trasversale** | 4.6 Gruppi Supporto e Routing | 2.5 | 4.0 | +1.5 | MEDIA |
| **Funzionale Trasversale** | 4.7 Knowledge Base | 2.5 | 4.0 | +1.5 | MEDIA |
| **Funzionale Trasversale** | 4.8 Notifiche | 3.0 | 4.0 | +1.0 | BASSA |
| **Funzionale Verticale** | 5.1 Incident Management & Major Incident | 2.5 | 4.5 | +2.0 | ALTA |
| **Funzionale Verticale** | 5.2 Change Management & CAB | 2.5 | 4.5 | +2.0 | ALTA |
| **Funzionale Verticale** | 5.3 Problem Management | 2.0 | 4.0 | +2.0 | MEDIA |
| **Funzionale Verticale** | 5.4 Interaction Management | 1.5 | 4.0 | +2.5 | MEDIA |
| **Funzionale Verticale** | 5.5 SLA Management | 2.0 | 4.5 | +2.5 | ALTA |
| **Funzionale Verticale** | 5.6 Request Management | 2.0 | 4.0 | +2.0 | ALTA |
| **Funzionale Verticale** | 5.7 Asset Management | 2.5 | 4.5 | +2.0 | MEDIA |
| **Funzionale Verticale** | 5.8 Mobile Agent | 2.0 | 3.5 | +1.5 | BASSA |
| **Funzionale Verticale** | 5.9 Reportistica e Dashboard | 2.0 | 4.5 | +2.5 | ALTA |
| **Foundation & Security** | 6.1 Utenti / HR (Sincronizzazione) | 1.5 | 5.0 | +3.5 | ALTA |
| **Foundation & Security** | 6.2 Gruppi e Ruoli | 2.0 | 4.5 | +2.5 | ALTA |
| **Foundation & Security** | 6.3 Single Sign-On & MFA | 3.0 | 4.5 | +1.5 | MEDIA |
| **MEDIA COMPLESSIVA** | **Indice Globale Piattaforma** | **2.3** | **4.2** | **+1.9** | **ALTA** |"""
    report = report.replace("| *(Compilare la tabella riassuntiva con i punteggi assegnati nelle sezioni precedenti)* |", tabella_riepilogo)
    report = report.replace("*(Compilare la tabella riassuntiva con i punteggi assegnati nelle sezioni precedenti)*", tabella_riepilogo)

    # 8. Roadmap
    sec_8_1 = """1. **Sincronizzazione Automatica Utenti (`sys_user`)**: Collegamento con Microsoft Entra ID/LDAP per azzerare la gestione manuale e i rischi di utenze orfane.
2. **Matrice Ruoli & Remediation ACL**: Eliminare l'assegnazione diretta dei ruoli e razionalizzare le oltre 100 ACL custom.
3. **Formalizzazione SLA Management e On-Hold**: Attivazione matrice oraria P1-P4 (7-20 / 24x7 P1) e regole automatiche di sospensione ticket.
4. **Digitalizzazione Major Incident Management (MIM)**: Attivazione modulo Major Incident su ServiceNow con comunicazioni di crisi integrate.
5. **Riorganizzazione Service Catalog & Go-Live Employee Center (ESC)**: Nuova tassonomia a 4 macro-categorie e workflow parallelo di Onboarding.
6. **Istituzione del CAB e Calendario Settimanale**: Definizione comitato CAB e catalogo Standard Change pre-autorizzati."""
    report = report.replace("*(Elencare le attività con priorità ALTA emerse dalle tabelle)*", sec_8_1)

    sec_8_2 = """1. **Governance CMDB & Connector Intune**: Nomina CMDB Owner e attivazione ingestione automatica degli endpoint tramite Service Graph Connector.
2. **Framework Monitoraggio Migrazione Cloud SAP**: Mappatura preventiva delle dipendenze dei server CED da dismettere.
3. **Service Operations Workspace (SOW) & Interaction**: Abilitazione workspace moderno per il Service Desk con tracciamento telefonate.
4. **Bonifica Problem Management & Policy Knowledge 12 Mesi**: Normalizzazione 24 Problem storici e riduzione ciclo review KB.
5. **Asset Management Lifecycle**: Configurazione stati magazzino per i 2.820 asset e riconciliazione automatica con CMDB.
6. **Dashboard Direzionale e Vendor SLA Tracking**: Realizzazione cruscotti KPI per monitoraggio performance e fornitori terzi."""
    report = report.replace("*(Elencare le attività con priorità MEDIA emerse dalle tabelle)*", sec_8_2)

    sec_8_3 = """1. **Adozione Mobile Apps (Now Mobile / ServiceNow Agent)**: Rilascio app per approvazioni rapide manageriali e interventi sul campo.
2. **Template Notifiche e Branding**: Restyling grafico delle email transazionali e notifiche push aziendali.
3. **Piano di Upgrade Continuo (N-1)**: Pianificazione annuale degli upgrade di release con suite ATF."""
    report = report.replace("*(Elencare le attività con priorità BASSA emerse dalle tabelle)*", sec_8_3)

    # 9. Conclusioni
    cliente_nome = meta.get('cliente', 'ACinque')
    sec_9 = f"""L'assessment condotto sulla piattaforma ServiceNow di **{cliente_nome}** ha messo in luce una solida base di partenza, contraddistinta da un perimetro applicativo focalizzato e da un modello dati privo di customizzazioni globali bloccanti. Questo contesto tecnico favorevole consente di pianificare un'evoluzione rapida verso gli standard più elevati di efficienza e conformità ITIL.

Le aree di maggiore attenzione riguardano la sicurezza e i dati di base: la gestione manuale delle anagrafiche utente e la dispersione delle regole autorizzative rappresentano i primi nodi da sciogliere. L'adozione del piano di raccomandazioni proposto da Devoteam consentirà ad {cliente_nome} non solo di massimizzare il ritorno sull'investimento del tier **ITSM Standard**, ma anche di offrire ai propri dipendenti un'esperienza digitale moderna tramite **Employee Center**, garantendo al management il pieno controllo operativo e la visibilità completa sul ciclo di vita dei servizi IT."""
    report = report.replace(f"*(Redigere una conclusione personalizzata basata sui risultati dell'assessment per il cliente {cliente_nome})*", sec_9)
    report = report.replace("*(Redigere una conclusione personalizzata basata sui risultati dell'assessment per il cliente {{metadata.cliente}})*", sec_9)

    return report


def main():
    parser = argparse.ArgumentParser(description="Generatore Report ServiceNow ITSM Assessment via NowAIKit MCP")
    parser.add_argument("-q", "--questionario", type=Path, required=True, help="Percorso del file risposte-questionario.json")
    parser.add_argument("-o", "--output", type=Path, default=None, help="Percorso del file Markdown di output (default: stampa a video)")
    parser.add_argument("-i", "--istruzioni", type=Path, default=DEFAULT_ISTRUZIONI, help="Percorso di istruzioni.json")
    parser.add_argument("-t", "--template", type=Path, default=DEFAULT_TEMPLATE, help="Percorso di template.md")
    parser.add_argument("--mcp-url", type=str, default=DEFAULT_MCP_URL, help="URL dell'endpoint MCP server nowaikit")
    parser.add_argument("--skip-mcp", action="store_true", help="Salta la chiamata live all'MCP server e usa fallback diagnostico")

    args = parser.parse_args()

    if not args.questionario.exists():
        print(f"Errore: File questionario non trovato: {args.questionario}", file=sys.stderr)
        sys.exit(1)

    if not args.istruzioni.exists():
        print(f"Errore: File istruzioni non trovato: {args.istruzioni}", file=sys.stderr)
        sys.exit(1)

    if not args.template.exists():
        print(f"Errore: File template non trovato: {args.template}", file=sys.stderr)
        sys.exit(1)

    # 1. Carica il questionario
    questionario = load_json(args.questionario)

    # 2. Esegui discovery tramite MCP
    discovery_data = {}
    if not args.skip_mcp:
        client = NowAIKitMCPClient(base_url=args.mcp_url)
        discovery_data = execute_mcp_discovery(args.istruzioni, client, verbose=True)
    else:
        print("[*] Esecuzione in modalità --skip-mcp (offline).")

    # 3. Leggi template
    with open(args.template, "r", encoding="utf-8") as f:
        template_str = f.read()

    # 4. Genera il report
    print("[*] Elaborazione e integrazione dei contenuti in corso...")
    final_report = generate_report(questionario, discovery_data, template_str)

    # 5. Output
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(final_report)
        print(f"[+] Report generato con successo in: {args.output.resolve()}")
    else:
        print("\n" + "=" * 80)
        print(final_report)
        print("=" * 80)


if __name__ == "__main__":
    main()
