#!/usr/bin/env bash
# ==============================================================================
# UTILS.SH — Funzioni di utilità per notifiche Telegram ed Email del Homelab
# ==============================================================================
# - Zero plaintext secrets: caricamento sicuro on-the-fly tramite SOPS da secrets-sops/
# - Telegram: invio immediato tramite curl HTML (API sendMessage)
# - Email HTML: motore diretto SMTP SSL (smtp.gmail.com:465) con standard library Python
#   supporto allegati (log completo in caso di errore) e fallback automatico Telegram
# ==============================================================================

UTILS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$UTILS_DIR/../.." && pwd)"

DEFAULT_EMAIL_RECIPIENT="${DEFAULT_EMAIL_RECIPIENT:-o.pindaro@gmail.com}"
DEFAULT_EMAIL_FROM="${DEFAULT_EMAIL_FROM:-o.pindaro@gmail.com}"
SMTP_HOST="${SMTP_HOST:-smtp.gmail.com}"
SMTP_PORT="${SMTP_PORT:-465}"
SMTP_USER="${SMTP_USER:-o.pindaro@gmail.com}"

# Caricamento dinamico dei segreti in memoria via SOPS (senza file in chiaro)
_load_notification_secrets() {
    # 1. Telegram Secrets
    if [ -z "${TELEGRAM_BOT_TOKEN:-}" ] && command -v sops >/dev/null 2>&1 && [ -f "${ROOT_DIR}/secrets-sops/alertmanager-telegram.enc.yaml" ]; then
        TELEGRAM_BOT_TOKEN="$(sops -d --extract '["stringData"]["token"]' "${ROOT_DIR}/secrets-sops/alertmanager-telegram.enc.yaml" 2>/dev/null || true)"
        TELEGRAM_CHAT_ID="$(sops -d --extract '["stringData"]["chat_id"]' "${ROOT_DIR}/secrets-sops/alertmanager-telegram.enc.yaml" 2>/dev/null || true)"
    fi

    # 2. SMTP Secrets
    if [ -z "${SMTP_PASS:-}" ] && command -v sops >/dev/null 2>&1 && [ -f "${ROOT_DIR}/secrets-sops/smtp-creds.enc.yaml" ]; then
        SMTP_HOST="$(sops -d --extract '["stringData"]["smtp-host"]' "${ROOT_DIR}/secrets-sops/smtp-creds.enc.yaml" 2>/dev/null || echo "smtp.gmail.com")"
        SMTP_PORT="$(sops -d --extract '["stringData"]["smtp-port"]' "${ROOT_DIR}/secrets-sops/smtp-creds.enc.yaml" 2>/dev/null || echo "465")"
        SMTP_USER="$(sops -d --extract '["stringData"]["smtp-user"]' "${ROOT_DIR}/secrets-sops/smtp-creds.enc.yaml" 2>/dev/null || echo "o.pindaro@gmail.com")"
        SMTP_PASS="$(sops -d --extract '["stringData"]["smtp-pass"]' "${ROOT_DIR}/secrets-sops/smtp-creds.enc.yaml" 2>/dev/null || true)"
        DEFAULT_EMAIL_FROM="$(sops -d --extract '["stringData"]["smtp-from"]' "${ROOT_DIR}/secrets-sops/smtp-creds.enc.yaml" 2>/dev/null || echo "o.pindaro@gmail.com")"
    fi
}

# Invia un messaggio Telegram formattato in HTML
# Uso: send_telegram <messaggio_html> [titolo_opzionale]
send_telegram() {
    local msg="$1"
    local title="${2:-}"
    local full_text="$msg"

    _load_notification_secrets

    if [ -n "$title" ]; then
        full_text="<b>${title}</b>%0A%0A${msg}"
    fi

    if [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_CHAT_ID:-}" ]; then
        curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            -d chat_id="${TELEGRAM_CHAT_ID}" \
            -d parse_mode="HTML" \
            -d text="${full_text}" >/dev/null 2>&1 || true
    fi
}

# Costruisce il template HTML responsive unificato del Homelab
# Uso: build_html_email_template <icona> <titolo_principale> <sottotitolo> <badge_status> <colore_badge> <dettagli_table_html> [sezione_extra_html]
build_html_email_template() {
    local icon="$1"
    local main_title="$2"
    local subtitle="$3"
    local badge_status="$4"
    local badge_color="${5:-#10b981}"  # default verde (#10b981), blu (#3b82f6) o rosso (#ef4444)
    local table_rows="$6"
    local extra_section="${7:-}"

    cat <<EOF
<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>$main_title</title>
</head>
<body style="margin: 0; padding: 20px; background-color: #f1f5f9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1e293b;">
  <div style="max-width: 620px; margin: 0 auto; background: #ffffff; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06); border: 1px solid #e2e8f0;">
    <!-- Header Dark Gradient -->
    <div style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); padding: 24px; color: #ffffff;">
      <table style="width: 100%; border-collapse: collapse;">
        <tr>
          <td style="font-size: 26px; vertical-align: middle;">$icon</td>
          <td style="text-align: right; vertical-align: middle;">
            <span style="background-color: ${badge_color}; color: #ffffff; font-size: 11px; font-weight: 700; text-transform: uppercase; padding: 4px 10px; border-radius: 9999px; letter-spacing: 0.05em; display: inline-block;">$badge_status</span>
          </td>
        </tr>
      </table>
      <h2 style="margin: 12px 0 4px 0; font-size: 18px; font-weight: 700; color: #ffffff; line-height: 1.3;">$main_title</h2>
      <p style="margin: 0; font-size: 12px; color: #94a3b8;">$subtitle</p>
    </div>

    <!-- Body Content -->
    <div style="padding: 24px;">
      <h3 style="margin: 0 0 14px 0; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #64748b; border-bottom: 2px solid #f1f5f9; padding-bottom: 6px;">Dettagli Operazione</h3>

      <table style="width: 100%; border-collapse: collapse; margin-bottom: 16px; font-size: 13px;">
        <tbody>
          $table_rows
        </tbody>
      </table>

      $extra_section
    </div>

    <!-- Footer -->
    <div style="background-color: #f8fafc; padding: 14px 24px; font-size: 11px; color: #94a3b8; border-top: 1px solid #e2e8f0; text-align: center;">
      Servizio di Notifica Automatico Homelab · Power Orchestration
    </div>
  </div>
</body>
</html>
EOF
}

# Invia email riassuntiva HTML con supporto allegato e fallback su Telegram
# Uso: send_summary_email <destinatario> <titolo> <body_html> <messaggio_fallback_telegram> [percorso_file_allegato]
send_summary_email() {
    local recipient="${1:-$DEFAULT_EMAIL_RECIPIENT}"
    local title="$2"
    local body="$3"
    local fallback_text="${4:-$title}"
    local attachment="${5:-}"
    local email_sent=false

    _load_notification_secrets

    # Tentativo primario: invio diretto SMTP SSL via Python (standard library, zero dipendenze)
    if [ -n "$recipient" ] && [ -n "${SMTP_PASS:-}" ] && command -v python3 >/dev/null 2>&1; then
        echo "📧 Invio email via SMTP SSL ($SMTP_HOST:$SMTP_PORT) a $recipient..."
        if python3 -c '
import sys, smtplib, ssl, os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

host = sys.argv[1]
port = int(sys.argv[2])
user = sys.argv[3]
password = sys.argv[4]
sender = sys.argv[5]
recipient = sys.argv[6]
subject = sys.argv[7]
html_body = sys.argv[8]
attachment_path = sys.argv[9] if len(sys.argv) > 9 and sys.argv[9] else ""

msg = MIMEMultipart("mixed")
msg["Subject"] = subject
msg["From"] = sender
msg["To"] = recipient

part_html = MIMEText(html_body, "html", "utf-8")
msg.attach(part_html)

if attachment_path and os.path.isfile(attachment_path):
    filename = os.path.basename(attachment_path)
    with open(attachment_path, "rb") as f:
        part_attach = MIMEApplication(f.read(), Name=filename)
    part_attach["Content-Disposition"] = f"attachment; filename=\"{filename}\""
    msg.attach(part_attach)

context = ssl.create_default_context()
with smtplib.SMTP_SSL(host, port, context=context, timeout=15) as server:
    server.login(user, password)
    server.send_message(msg)
' "$SMTP_HOST" "$SMTP_PORT" "$SMTP_USER" "$SMTP_PASS" "$DEFAULT_EMAIL_FROM" "$recipient" "$title" "$body" "$attachment" >/dev/null 2>&1; then
            email_sent=true
        else
            echo "⚠️ Invio SMTP diretto fallito, tento sendmail locale..."
        fi
    fi

    # Tentativo secondario: Postfix sendmail locale (se SMTP diretto non disponibile o fallito)
    if [ "$email_sent" != "true" ] && [ -n "$recipient" ] && command -v sendmail >/dev/null 2>&1; then
        echo "📧 Tentativo invio tramite sendmail locale a $recipient..."
        local boundary="===HOMELAB_MIME_$(date +%s)==="
        if [ -n "$attachment" ] && [ -f "$attachment" ]; then
            if cat <<EOF | sendmail -t
From: ${DEFAULT_EMAIL_FROM}
To: ${recipient}
Subject: ${title}
MIME-Version: 1.0
Content-Type: multipart/mixed; boundary="${boundary}"

--${boundary}
Content-Type: text/html; charset=UTF-8
Content-Transfer-Encoding: 7bit

${body}

--${boundary}
Content-Type: text/plain; name="$(basename "$attachment")"
Content-Disposition: attachment; filename="$(basename "$attachment")"
Content-Transfer-Encoding: base64

$(base64 < "$attachment")
--${boundary}--
EOF
            then
                email_sent=true
            fi
        else
            if cat <<EOF | sendmail -t
From: ${DEFAULT_EMAIL_FROM}
To: ${recipient}
Subject: ${title}
MIME-Version: 1.0
Content-Type: text/html; charset=UTF-8

${body}
EOF
            then
                email_sent=true
            fi
        fi
    fi

    # Fallback finale su Telegram se l'email non è stata recapitata
    if [ "$email_sent" != "true" ]; then
        echo "⚠️ Fallback: invio avviso di backup via Telegram..."
        send_telegram "$fallback_text" "$title"
    else
        echo "✅ Email inviata con successo."
    fi
}

# Auto-caricamento al sourcing
_load_notification_secrets
