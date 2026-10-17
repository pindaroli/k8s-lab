#!/usr/bin/env python3
"""
cleanup_torrents.py
Motore CLI interattivo per la ricerca, filtraggio avanzato temporale,
percentuale e per categoria, gestione delle eccezioni e cancellazione
atomica dei torrent (inclusi i file scaricati su disco) via REST API qBittorrent.
Utilizza esclusivamente moduli della libreria standard di Python (zero dipendenze).
"""

import os
import sys
import re
import json
import ssl
import subprocess
import urllib.request
import urllib.parse
import urllib.error
import http.cookiejar
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Set, Tuple, Optional, Any
import argparse

# Risoluzione dinamica della root per CWD independence (go-launcher-script-pattern)
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
os.chdir(ROOT_DIR)

# Costanti colori ANSI per l'interfaccia terminale
class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    RESET = "\033[0m"


def load_sops_credential(key_name: str) -> Optional[str]:
    """Tenta il recupero di una credenziale da secrets-sops/servarr-api-keys.enc.yaml via SOPS."""
    sops_file = os.path.join(ROOT_DIR, "secrets-sops", "servarr-api-keys.enc.yaml")
    if not os.path.isfile(sops_file):
        return None
    try:
        cmd = [
            "sops",
            "-d",
            "--extract",
            f'["stringData"]["{key_name}"]',
            sops_file,
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except Exception:
        return None


def format_bytes(bytes_val: int) -> str:
    """Formatta i bytes in unità leggibili (MB, GB, TB)."""
    if bytes_val < 0:
        return "0.00 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    val = float(bytes_val)
    idx = 0
    while val >= 1024.0 and idx < len(units) - 1:
        val /= 1024.0
        idx += 1
    return f"{val:.2f} {units[idx]}"


def format_timestamp(ts: int) -> str:
    """Converte un timestamp Unix in formato leggibile YYYY-MM-DD HH:MM:SS."""
    try:
        dt = datetime.fromtimestamp(ts)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(ts)


def parse_flexible_date(input_str: str, is_end_date: bool = False) -> datetime:
    """Interpreta date assolute (YYYY-MM-DD, YYYY-MM-DD HH:MM[:SS]) o alias temporali."""
    s = input_str.strip().lower()
    now_local = datetime.now()

    if not s or s in ("now", "today", "oggi"):
        if is_end_date:
            return now_local.replace(hour=23, minute=59, second=59, microsecond=999999)
        return now_local.replace(hour=0, minute=0, second=0, microsecond=0)

    if s in ("yesterday", "ieri"):
        y = now_local - timedelta(days=1)
        if is_end_date:
            return y.replace(hour=23, minute=59, second=59, microsecond=999999)
        return y.replace(hour=0, minute=0, second=0, microsecond=0)

    # Alias relativi: es. 7d, 30d, 2w, 1m
    m = re.match(r"^(\d+)\s*([dwmy])$", s)
    if m:
        qty = int(m.group(1))
        unit = m.group(2)
        if unit == "d":
            target = now_local - timedelta(days=qty)
        elif unit == "w":
            target = now_local - timedelta(weeks=qty)
        elif unit == "m":
            target = now_local - timedelta(days=qty * 30)
        elif unit == "y":
            target = now_local - timedelta(days=qty * 365)
        else:
            target = now_local
        if is_end_date:
            return target.replace(hour=23, minute=59, second=59, microsecond=999999)
        return target.replace(hour=0, minute=0, second=0, microsecond=0)

    # Formati standard
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(s, fmt)
            if is_end_date and fmt == "%Y-%m-%d":
                dt = dt.replace(hour=23, minute=59, second=59, microsecond=999999)
            return dt
        except ValueError:
            continue

    raise ValueError(
        f"Formato data non riconosciuto: '{input_str}'. Usa YYYY-MM-DD, YYYY-MM-DD HH:MM, o alias come 'today', '7d', '30d'."
    )


def parse_index_list(input_str: str, max_index: int) -> Set[int]:
    """Interpreta una stringa di indici ed intervalli separati da virgole (es: '1, 3, 5-8')."""
    indices: Set[int] = set()
    parts = [p.strip() for p in input_str.replace(";", ",").split(",") if p.strip()]
    for p in parts:
        if "-" in p:
            range_parts = p.split("-")
            if (
                len(range_parts) == 2
                and range_parts[0].strip().isdigit()
                and range_parts[1].strip().isdigit()
            ):
                start = int(range_parts[0].strip())
                end = int(range_parts[1].strip())
                if start > end:
                    start, end = end, start
                for idx in range(start, end + 1):
                    if 1 <= idx <= max_index:
                        indices.add(idx)
        elif p.isdigit():
            idx = int(p)
            if 1 <= idx <= max_index:
                indices.add(idx)
    return indices


class QBittorrentClient:
    """Client REST API v2 per qBittorrent, basato unicamente su urllib e standard library."""

    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password

        # Gestione cookie di sessione automatica
        self.cookie_jar = http.cookiejar.CookieJar()
        # Context SSL permissivo per certificati self-signed / interni
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE

        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookie_jar),
            urllib.request.HTTPSHandler(context=self.ssl_context),
        )

    def _request(
        self,
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
    ) -> Tuple[int, str]:
        """Esegue una chiamata HTTP/HTTPS verso l'endpoint specificato."""
        url = f"{self.base_url}{endpoint}"
        req_headers = {
            "User-Agent": "qbt-cleanup/1.0",
            "Referer": self.base_url,
        }
        if headers:
            req_headers.update(headers)

        encoded_data = None
        if data is not None:
            encoded_data = urllib.parse.urlencode(data).encode("utf-8")
            req_headers["Content-Type"] = "application/x-www-form-urlencoded"

        req = urllib.request.Request(
            url, data=encoded_data, headers=req_headers, method=method
        )
        try:
            with self.opener.open(req, timeout=timeout) as response:
                body = response.read().decode("utf-8", errors="replace")
                return response.status, body
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            return e.code, err_body
        except urllib.error.URLError as e:
            raise ConnectionError(f"Errore di rete verso {url}: {e.reason}")

    def login(self) -> bool:
        """Autenticazione all'API v2 (/api/v2/auth/login). Gestisce status 200 e 204."""
        status, body = self._request(
            "/api/v2/auth/login",
            method="POST",
            data={"username": self.username, "password": self.password},
        )
        if status in (200, 204):
            # Verifica presenza cookie SID o QBT_SID_*
            has_sid = False
            for cookie in self.cookie_jar:
                if "SID" in cookie.name.upper():
                    has_sid = True
                    break
            if has_sid or "Ok." in body or not body.strip():
                return True
        raise PermissionError(
            f"Autenticazione qBittorrent fallita (HTTP {status}): {body.strip()}"
        )

    def get_categories(self) -> List[str]:
        """Recupera la lista delle categorie censite da qBittorrent."""
        status, body = self._request("/api/v2/torrents/categories", method="GET")
        if status != 200:
            raise RuntimeError(f"Impossibile recuperare le categorie (HTTP {status}): {body}")
        try:
            data = json.loads(body)
            # data è un dizionario: {"category_name": {"name": "...", "savePath": "..."}, ...}
            if isinstance(data, dict):
                return sorted(list(data.keys()))
            return []
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Risposta JSON non valida da /torrents/categories: {e}")

    def get_torrents(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Recupera tutti i torrent da qBittorrent."""
        endpoint = "/api/v2/torrents/info"
        if category and category != "Tutte":
            endpoint += f"?category={urllib.parse.quote(category)}"
        status, body = self._request(endpoint, method="GET")
        if status != 200:
            raise RuntimeError(f"Impossibile recuperare i torrent (HTTP {status}): {body}")
        try:
            data = json.loads(body)
            if isinstance(data, list):
                return data
            return []
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Risposta JSON non valida da /torrents/info: {e}")

    def delete_torrents(self, hashes: List[str], delete_files: bool = True) -> bool:
        """Elimina i torrent specificati (in blocchi da 50 per evitare overflow di payload)."""
        if not hashes:
            return True

        chunk_size = 50
        for i in range(0, len(hashes), chunk_size):
            chunk = hashes[i : i + chunk_size]
            payload = {
                "hashes": "|".join(chunk),
                "deleteFiles": "true" if delete_files else "false",
            }
            status, body = self._request("/api/v2/torrents/delete", method="POST", data=payload)
            if status != 200:
                raise RuntimeError(
                    f"Errore durante l'eliminazione dei torrent (HTTP {status}): {body}"
                )
        return True


def run_interactive_wizard(
    client: QBittorrentClient,
    dry_run: bool = False,
    cli_args: Optional[argparse.Namespace] = None,
) -> None:
    """Esegue il wizard interattivo a 7 step secondo le specifiche dell'utente."""
    print(f"\n{Colors.CYAN}{Colors.BOLD}============================================================{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}   🧹 qBittorrent Selective Cleanup Tool                   {Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}============================================================{Colors.RESET}\n")

    # Autenticazione preventiva
    print(f"⏳ Connessione a qBittorrent ({client.base_url})...")
    client.login()
    print(f"{Colors.GREEN}✓ Autenticazione riuscita con successo.{Colors.RESET}\n")

    # 1. Input: <data start>
    dt_start = None
    if cli_args and cli_args.start:
        try:
            dt_start = parse_flexible_date(cli_args.start, is_end_date=False)
            print(f"• Data Inizio (da CLI): {Colors.BOLD}{dt_start.strftime('%Y-%m-%d %H:%M:%S')}{Colors.RESET}")
        except Exception as e:
            print(f"{Colors.RED}Data inizio specificata da CLI non valida: {e}{Colors.RESET}")

    while dt_start is None:
        raw_start = input(
            f"{Colors.YELLOW}[1] Inserisci data di inizio <data start>{Colors.RESET} (es. 2026-01-01, 7d, today) [default: 30d]: "
        ).strip()
        if not raw_start:
            raw_start = "30d"
        try:
            dt_start = parse_flexible_date(raw_start, is_end_date=False)
            print(f"  {Colors.GREEN}✓ Data inizio impostata a: {dt_start.strftime('%Y-%m-%d %H:%M:%S')}{Colors.RESET}\n")
        except Exception as e:
            print(f"  {Colors.RED}❌ {e}{Colors.RESET}")

    # 2. Input: <data end> (con validazione end >= start)
    dt_end = None
    if cli_args and cli_args.end:
        try:
            candidate_end = parse_flexible_date(cli_args.end, is_end_date=True)
            if candidate_end >= dt_start:
                dt_end = candidate_end
                print(f"• Data Fine (da CLI): {Colors.BOLD}{dt_end.strftime('%Y-%m-%d %H:%M:%S')}{Colors.RESET}")
            else:
                print(f"{Colors.RED}Data fine specificata da CLI deve essere >= data inizio.{Colors.RESET}")
        except Exception as e:
            print(f"{Colors.RED}Data fine specificata da CLI non valida: {e}{Colors.RESET}")

    while dt_end is None:
        raw_end = input(
            f"{Colors.YELLOW}[2] Inserisci data di fine <data end>{Colors.RESET} (più recente di <data start>, es. today, now) [default: today]: "
        ).strip()
        if not raw_end:
            raw_end = "today"
        try:
            candidate_end = parse_flexible_date(raw_end, is_end_date=True)
            if candidate_end < dt_start:
                print(
                    f"  {Colors.RED}❌ Errore: la data di fine ({candidate_end.strftime('%Y-%m-%d %H:%M:%S')}) deve essere più recente o uguale alla data di inizio ({dt_start.strftime('%Y-%m-%d %H:%M:%S')}).{Colors.RESET}"
                )
                continue
            dt_end = candidate_end
            print(f"  {Colors.GREEN}✓ Data fine impostata a: {dt_end.strftime('%Y-%m-%d %H:%M:%S')}{Colors.RESET}\n")
        except Exception as e:
            print(f"  {Colors.RED}❌ {e}{Colors.RESET}")

    # 3. Input: <perc>
    max_perc = None
    if cli_args and cli_args.perc is not None:
        if 0.0 <= cli_args.perc <= 100.0:
            max_perc = cli_args.perc
            print(f"• Percentuale massima di scaricamento (da CLI): {Colors.BOLD}{max_perc}%{Colors.RESET}")

    while max_perc is None:
        raw_perc = input(
            f"{Colors.YELLOW}[3] Inserisci percentuale massima di scaricamento <perc>{Colors.RESET} (0-100) [default: 100]: "
        ).strip()
        if not raw_perc:
            max_perc = 100.0
            print(f"  {Colors.GREEN}✓ Percentuale impostata a: 100%{Colors.RESET}\n")
            break
        try:
            val = float(raw_perc)
            if 0.0 <= val <= 100.0:
                max_perc = val
                print(f"  {Colors.GREEN}✓ Percentuale impostata a: {max_perc}%{Colors.RESET}\n")
            else:
                print(f"  {Colors.RED}❌ Inserisci un valore compreso tra 0 e 100.{Colors.RESET}")
        except ValueError:
            print(f"  {Colors.RED}❌ Valore non numerico valido.{Colors.RESET}")

    # 4. Input: Categoria
    print("⏳ Recupero categorie censite su qBittorrent...")
    categories = client.get_categories()
    selected_category = None

    if cli_args and cli_args.category:
        if cli_args.category.lower() in ("all", "tutte", "*"):
            selected_category = "Tutte"
        elif cli_args.category in categories:
            selected_category = cli_args.category
        else:
            print(f"{Colors.YELLOW}⚠️ Categoria '{cli_args.category}' non trovata tra quelle censite. Procedo interattivamente.{Colors.RESET}")

    while selected_category is None:
        print(f"\n{Colors.YELLOW}[4] Seleziona la Categoria:{Colors.RESET}")
        print(f"  [{Colors.BOLD}0{Colors.RESET}] Tutte (tutte le categorie) {Colors.GREEN}[DEFAULT]{Colors.RESET}")
        for idx, cat_name in enumerate(categories, 1):
            print(f"  [{Colors.BOLD}{idx}{Colors.RESET}] {cat_name}")

        raw_cat = input(f"\nScegli il numero della categoria [default: 0 - Tutte]: ").strip()
        if not raw_cat or raw_cat == "0":
            selected_category = "Tutte"
            print(f"  {Colors.GREEN}✓ Categoria selezionata: Tutte{Colors.RESET}\n")
            break
        if raw_cat.isdigit():
            c_idx = int(raw_cat)
            if 1 <= c_idx <= len(categories):
                selected_category = categories[c_idx - 1]
                print(f"  {Colors.GREEN}✓ Categoria selezionata: {selected_category}{Colors.RESET}\n")
                break
            else:
                print(f"  {Colors.RED}❌ Indice non valido.{Colors.RESET}")
        elif raw_cat in categories:
            selected_category = raw_cat
            print(f"  {Colors.GREEN}✓ Categoria selezionata: {selected_category}{Colors.RESET}\n")
            break
        else:
            print(f"  {Colors.RED}❌ Scelta non valida.{Colors.RESET}")

    # 4 bis. Ricerca torrent e filtraggio
    print(f"🔍 Ricerca torrent in corso con filtri applicati:")
    print(f"   - Data inserimento tra {Colors.BOLD}{dt_start.strftime('%Y-%m-%d %H:%M:%S')}{Colors.RESET} e {Colors.BOLD}{dt_end.strftime('%Y-%m-%d %H:%M:%S')}{Colors.RESET}")
    print(f"   - Completamento scaricamento <= {Colors.BOLD}{max_perc}%{Colors.RESET}")
    print(f"   - Categoria: {Colors.BOLD}{selected_category}{Colors.RESET}\n")

    start_ts = int(dt_start.timestamp())
    end_ts = int(dt_end.timestamp())

    all_torrents = client.get_torrents(category=selected_category if selected_category != "Tutte" else None)

    # Filtraggio rigoroso
    matched_torrents: List[Dict[str, Any]] = []
    for t in all_torrents:
        added_on = t.get("added_on", 0)
        progress_pct = round(t.get("progress", 0.0) * 100.0, 1)
        cat = t.get("category", "").strip()

        # Condizione temporale
        if not (start_ts <= added_on <= end_ts):
            continue

        # Condizione percentuale
        if progress_pct > max_perc:
            continue

        # Condizione categoria
        if selected_category != "Tutte" and cat != selected_category:
            continue

        matched_torrents.append(t)

    if not matched_torrents:
        print(f"{Colors.YELLOW}ℹ️  Nessun torrent trovato corrispondente ai criteri specificati.{Colors.RESET}")
        return

    # Ordinamento per data di inserimento (più recenti o più vecchi)
    matched_torrents.sort(key=lambda x: x.get("added_on", 0))

    # Stampa lista tabellare
    print(f"{Colors.BOLD}{'#':<4} {'Nome Torrent':<45} {'Categoria':<18} {'Compl.':<8} {'Data Inserimento':<20} {'Scaricato / Totale':<20}{Colors.RESET}")
    print("-" * 120)

    total_downloaded_bytes = 0
    total_nominal_bytes = 0

    for idx, t in enumerate(matched_torrents, 1):
        name = t.get("name", "N/A")
        if len(name) > 42:
            name = name[:39] + "..."
        cat = t.get("category", "") or "(nessuna)"
        if len(cat) > 16:
            cat = cat[:14] + ".."
        progress_str = f"{t.get('progress', 0.0) * 100.0:.1f}%"
        date_str = format_timestamp(t.get("added_on", 0))

        completed_bytes = t.get("completed", 0)
        size_bytes = t.get("size", t.get("total_size", 0))
        total_downloaded_bytes += completed_bytes
        total_nominal_bytes += size_bytes

        storage_str = f"{format_bytes(completed_bytes)} / {format_bytes(size_bytes)}"

        print(f"[{Colors.CYAN}{idx:^2}{Colors.RESET}] {name:<45} {cat:<18} {progress_str:<8} {date_str:<20} {storage_str:<20}")

    print("-" * 120)
    print(
        f"{Colors.BOLD}Totale candidati:{Colors.RESET} {len(matched_torrents)} torrent | "
        f"{Colors.BOLD}Spazio scaricato:{Colors.RESET} {Colors.GREEN}{format_bytes(total_downloaded_bytes)}{Colors.RESET} "
        f"({format_bytes(total_nominal_bytes)} nominali)\n"
    )

    # 5. Input: Esclusioni
    excluded_indices: Set[int] = set()
    if cli_args and cli_args.exclude:
        excluded_indices = parse_index_list(cli_args.exclude, len(matched_torrents))
        print(f"• Esclusioni impostate da CLI: {sorted(list(excluded_indices))}")
    else:
        has_exclusions = input(
            f"{Colors.YELLOW}[5] Ci sono esclusioni da non cancellare?{Colors.RESET} (y/N) [default: no]: "
        ).strip().lower()

        if has_exclusions in ("y", "yes", "s", "si"):
            raw_excl = input(
                f"  Inserisci gli indici da escludere separati da virgola (es: 1, 3, 5-8): "
            ).strip()
            excluded_indices = parse_index_list(raw_excl, len(matched_torrents))
            if excluded_indices:
                print(f"  {Colors.GREEN}✓ Torrent esclusi salvati ({len(excluded_indices)}):{Colors.RESET}")
                for ex_idx in sorted(list(excluded_indices)):
                    t_name = matched_torrents[ex_idx - 1].get("name", "")
                    if len(t_name) > 50:
                        t_name = t_name[:47] + "..."
                    print(f"    • [#{ex_idx}] {t_name}")
                print()
            else:
                print(f"  {Colors.YELLOW}Nessun indice valido inserito. Nessuna esclusione applicata.{Colors.RESET}\n")

    # Calcolo lista netta di eliminazione
    final_to_delete: List[Tuple[int, Dict[str, Any]]] = []
    final_freed_bytes = 0
    final_nominal_bytes = 0

    for idx, t in enumerate(matched_torrents, 1):
        if idx not in excluded_indices:
            final_to_delete.append((idx, t))
            final_freed_bytes += t.get("completed", 0)
            final_nominal_bytes += t.get("size", t.get("total_size", 0))

    if not final_to_delete:
        print(f"{Colors.GREEN}Tutti i torrent candidati sono stati esclusi. Nessuna operazione da eseguire.{Colors.RESET}")
        return

    # 6. Conferma di sicurezza
    print(f"\n{Colors.RED}{Colors.BOLD}⚠️  ATTENZIONE DI SICUREZZA:{Colors.RESET}")
    print(
        f"Stai per eliminare definitivamente {Colors.BOLD}{len(final_to_delete)}{Colors.RESET} torrent "
        f"e {Colors.RED}{Colors.BOLD}TUTTI i relativi file dal disco!{Colors.RESET}"
    )
    print(f"Spazio fisico stimato da liberare su disco: {Colors.GREEN}{Colors.BOLD}{format_bytes(final_freed_bytes)}{Colors.RESET}\n")

    confirmed = False
    if cli_args and cli_args.yes:
        confirmed = True
        print("• Conferma automatica via flag --yes.")
    else:
        conf_input = input(
            f"{Colors.YELLOW}[6] Confermi la cancellazione definitiva?{Colors.RESET} (Digitare {Colors.BOLD}'yes'{Colors.RESET} per confermare): "
        ).strip().lower()
        if conf_input in ("yes", "si"):
            confirmed = True

    if not confirmed:
        print(f"\n{Colors.YELLOW}❌ Operazione annullata dall'utente. Nessun dato eliminato o modificato.{Colors.RESET}")
        return

    # Esecuzione cancellazione
    hashes_to_delete = [t.get("hash", "") for _, t in final_to_delete if t.get("hash")]

    if dry_run:
        print(f"\n{Colors.BLUE}[DRY-RUN] Simulazione eliminazione di {len(hashes_to_delete)} torrent completata (nessuna chiamata REST distruttiva inviata).{Colors.RESET}")
    else:
        print(f"\n⏳ Eliminazione definitiva di {len(hashes_to_delete)} torrent e file su qBittorrent in corso...")
        client.delete_torrents(hashes_to_delete, delete_files=True)
        print(f"{Colors.GREEN}✓ Eliminazione completata con successo!{Colors.RESET}")

    # 7. Stampa riepilogo
    freed_gb = final_freed_bytes / (1024.0**3)
    nominal_gb = final_nominal_bytes / (1024.0**3)

    print(f"\n{Colors.GREEN}{Colors.BOLD}============================================================{Colors.RESET}")
    print(f"{Colors.GREEN}{Colors.BOLD}   ✅ RIEPILOGO OPERAZIONE DI PULIZIA                      {Colors.RESET}")
    print(f"{Colors.GREEN}{Colors.BOLD}============================================================{Colors.RESET}")
    print(f"• Torrent eliminati: {Colors.BOLD}{len(final_to_delete)}{Colors.RESET}")
    print(f"• Spazio su disco recuperato: {Colors.BOLD}{Colors.GREEN}{freed_gb:.2f} GB{Colors.RESET} ({format_bytes(final_freed_bytes)})")
    if nominal_gb > freed_gb:
        print(f"• Spazio nominale dei torrent: {nominal_gb:.2f} GB ({format_bytes(final_nominal_bytes)})")
    print(f"{Colors.GREEN}{Colors.BOLD}============================================================{Colors.RESET}\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Tool CLI interattivo per la pulizia selettiva dei torrent su qBittorrent."
    )
    parser.add_argument(
        "--url",
        default=os.environ.get("QBT_URL", "http://10.10.20.50:8080"),
        help="URL base di qBittorrent (default: $QBT_URL o http://10.10.20.50:8080)",
    )
    parser.add_argument(
        "--user",
        default=os.environ.get("QBT_USER", "admin"),
        help="Username qBittorrent (default: $QBT_USER o admin)",
    )
    parser.add_argument(
        "--pass",
        dest="password",
        default=os.environ.get("QBT_PASS"),
        help="Password qBittorrent (default: $QBT_PASS o recupero automatico via SOPS)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simula la ricerca e l'eliminazione senza inviare comandi distruttivi all'API.",
    )
    parser.add_argument("--start", help="Data di inizio preimpostata (YYYY-MM-DD, 7d, 30d)")
    parser.add_argument("--end", help="Data di fine preimpostata (YYYY-MM-DD, today, now)")
    parser.add_argument("--perc", type=float, help="Percentuale massima di completamento (0-100)")
    parser.add_argument("--category", help="Categoria preimpostata (o 'Tutte')")
    parser.add_argument("--exclude", help="Elenco indici da escludere (es: '1, 3, 5-8')")
    parser.add_argument("--yes", action="store_true", help="Salta la conferma finale di sicurezza")

    args = parser.parse_args()

    # Risoluzione password se non fornita
    password = args.password
    if not password:
        password = load_sops_credential("qbittorrent-pass")
    if not password:
        print(
            f"{Colors.RED}❌ Password qBittorrent non trovata. Imposta $QBT_PASS, usa --pass, o verifica secrets-sops/servarr-api-keys.enc.yaml.{Colors.RESET}"
        )
        sys.exit(1)

    username = args.user
    if not username:
        username = load_sops_credential("qbittorrent-user") or "admin"

    client = QBittorrentClient(
        base_url=args.url,
        username=username,
        password=password,
    )

    try:
        run_interactive_wizard(client, dry_run=args.dry_run, cli_args=args)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Operazione interrotta dall'utente.{Colors.RESET}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{Colors.RED}❌ Errore durante l'esecuzione: {e}{Colors.RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()
