#!/usr/bin/env bash
# ==============================================================================
# UTILS.SH — Funzioni di utilità per notifiche Telegram ed Email su PVE3
# ==============================================================================
# Progettato per mantenere la stessa interfaccia e stile grafico di
# custom-normalizer/utils.sh (normalize.sh), con motore nativo bash (curl + sendmail)
# senza dipendenze Python/Apprise esterne sull'hypervisor.
# ==============================================================================

TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-6548622283:AAHUfcvGWfj8LBdd_V4420uctNCKk3-D_Xs}"
TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-554585346}"
DEFAULT_EMAIL_RECIPIENT="${DEFAULT_EMAIL_RECIPIENT:-o.pindaro@gmail.com}"
DEFAULT_EMAIL_FROM="${DEFAULT_EMAIL_FROM:-o.pindaro@gmail.com}"

# Invia un messaggio Telegram formattato in HTML
# Uso: send_telegram <messaggio_html> [titolo_opzionale]
send_telegram() {
    local msg="$1"
    local title="${2:-}"
    local full_text="$msg"

    if [ -n "$title" ]; then
        full_text="<b>${title}</b>%0A%0A${msg}"
    fi

    if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ]; then
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
    local badge_color="${5:-#10b981}"  # default verde (#10b981) o rosso (#ef4444)
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
      Servizio di Notifica Automatico Homelab · Proxmox PVE3 Orchestration
    </div>
  </div>
</body>
</html>
EOF
}

# Invia email riassuntiva HTML con fallback su Telegram
# Uso: send_summary_email <destinatario> <titolo> <body_html> <messaggio_fallback_telegram>
send_summary_email() {
    local recipient="${1:-$DEFAULT_EMAIL_RECIPIENT}"
    local title="$2"
    local body="$3"
    local fallback_text="${4:-$title}"
    local email_sent=false

    if [ -n "$recipient" ] && command -v sendmail >/dev/null 2>&1; then
        echo "📧 Invio email di riepilogo a $recipient..."

        # Invio tramite Postfix locale con header MIME HTML
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
        else
            echo "⚠️ Invio sendmail fallito."
        fi
    fi

    # Se l'invio email è fallito o sendmail non è disponibile, scatta il fallback Telegram
    if [ "$email_sent" != "true" ]; then
        echo "⚠️ Fallback: invio avviso di backup via Telegram..."
        send_telegram "$fallback_text" "$title"
    fi
}
