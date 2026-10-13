Ecco un riassunto tecnico e strutturato, pronto da incollare come prompt di contesto o specifica funzionale per un agent in Antigravity:

# Obiettivo
Implementare/configurare uno spazio Telegram organizzato a sezioni tematiche isolate (stile server Discord), ottimizzato per la gestione a singolo amministratore (zero manutenzione e anti-spam nativo) tramite l'architettura **Supergruppo con Topic in sola lettura**.

---

### Architettura & Pattern di Riferimento
- **Entità Telegram:** Supergruppo (ID tipo `-100...`) con flag `is_forum = true`.
- **Modello di autorizzazione:** RBAC semplificato in modalità "Bacheca Unidirezionale" (Broadcast).
  - Permessi globali membri ordinari: `can_send_messages = false` (ereditato a cascata da tutti i topic, bloccando testi, media, sticker e link).
  - Permessi admin/bot: Privilegi completi di scrittura, pinning e creazione/gestione topic.
- **Topologia:** Lista piana di topic dedicati per argomento (es. `📢 Annunci`, `📦 Release`, `📖 Documentazione`, `🛡️ Security`), ciascuno con `icon_custom_emoji_id` identificativa.
- **Gestione Notifiche:** Gerarchica. L'utente riceve notifiche push contestuali (`[NomeGruppo › NomeTopic]: testo`) con facoltà di mutare selettivamente singoli topic o l'intero hub. Supporto a `disable_notification = true` (invio silente) e pin con notifica forzata per messaggi critici.

---

### Specifiche Tecniche per Telegram Bot API
1. **Creazione / Configurazione Topic:**
   - Metodo `createForumTopic`:
     - Parametri: `chat_id`, `name`, `icon_color` (opzionale), `icon_custom_emoji_id` (opzionale).
     - Output: `message_thread_id` (da mappare e persistere per l'indirizzamento dei successivi invii).
2. **Restrizione Scrittura Globale (Sola Lettura):**
   - Metodo `setChatPermissions`:
     - Parametri: `chat_id`, oggetto `ChatPermissions` con tutti i flag di invio impostati a `false` (`can_send_messages=false`, `can_send_audios=false`, `can_send_documents=false`, `can_send_photos=false`, `can_send_videos=false`, `can_send_other_messages=false`, `can_add_web_page_previews=false`).
3. **Dispatch dei Messaggi Tematici:**
   - Metodi `sendMessage`, `sendPhoto`, `sendDocument`, ecc.:
     - Parametro obbligatorio: `message_thread_id` valorizzato con l'ID del topic target per evitare il fallback sul topic generale.
     - Parametro notifica: `disable_notification = true | false` a seconda dell'urgenza.
4. **Fissaggio e Alert Critici:**
   - Metodo `pinChatMessage`:
     - Parametri: `chat_id`, `message_id`, `disable_notification = false` per scatenare la notifica forzata ai membri del topic.

---

### Requisiti del Modulo di Automazione
- Mappare i canali logici dell'applicazione (es. eventi, log, report, avvisi) ai corrispondenti `message_thread_id`.
- Fornire un'interfaccia/wrapper unificato per l'invio che accetti: `target_topic`, `payload_text`, `media_files (opzionale)` e `silent_mode (bool)`.
- Prevedere la gestione del `General Topic` (thread ID predefinito) per comunicazioni di servizio o info generali di benvenuto.