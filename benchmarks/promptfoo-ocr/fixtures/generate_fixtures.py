#!/usr/bin/env python3
"""
Generatore di documenti campione per i test OCR con Promptfoo.
Utilizza ImageMagick (magick) con font esplicito /System/Library/Fonts/Helvetica.ttc.
"""

import os
import subprocess

FIXTURES_DIR = os.path.dirname(os.path.abspath(__file__))
FONT = "/System/Library/Fonts/Helvetica.ttc"

def generate_fattura():
    png_path = os.path.join(FIXTURES_DIR, "fattura_test.png")
    cmd = [
        "magick",
        "-size", "900x1100",
        "xc:white",
        "-font", FONT,

        # Header aziendale
        "-pointsize", "26", "-fill", "#1e293b",
        "-draw", "text 50,60 'TECH SOLUTIONS S.R.L.'",
        "-pointsize", "14", "-fill", "#64748b",
        "-draw", "text 50,90 'Via dell Innovazione 42 - 00100 Roma (RM)'",
        "-draw", "text 50,110 'Partita IVA: IT01234567890 | PEC: techsolutions@pec.it'",

        # Linea divisoria
        "-stroke", "#cbd5e1", "-strokewidth", "2",
        "-draw", "line 50,130 850,130",
        "-stroke", "none",

        # Titolo Fattura
        "-pointsize", "22", "-fill", "#0f172a",
        "-draw", "text 50,170 'FATTURA N. FT-2026-089'",
        "-pointsize", "16", "-fill", "#334155",
        "-draw", "text 650,170 'Data: 11/10/2026'",

        # Dati Cliente
        "-pointsize", "14", "-fill", "#475569",
        "-draw", "text 50,220 'DESTINATARIO:'",
        "-pointsize", "16", "-fill", "#0f172a",
        "-draw", "text 50,245 'Homelab System Services'",
        "-pointsize", "14", "-fill", "#334155",
        "-draw", "text 50,270 'Via dei Server 10 - 20100 Milano'",
        "-draw", "text 50,290 'Codice Fiscale: HMLSRV80A01H501U'",

        # Tabella Header
        "-fill", "#0284c7",
        "-draw", "rectangle 50,330 850,370",
        "-pointsize", "14", "-fill", "white",
        "-draw", "text 70,356 'DESCRIZIONE ARTICOLO'",
        "-draw", "text 520,356 'Q.TA'",
        "-draw", "text 620,356 'PREZZO UNIT.'",
        "-draw", "text 750,356 'TOTALE'",

        # Riga 1
        "-pointsize", "14", "-fill", "#1e293b",
        "-draw", "text 70,405 'Mini-PC AMD Ryzen AI 9 HX 370 64GB LPDDR5'",
        "-draw", "text 530,405 '1'",
        "-draw", "text 630,405 '850.00 EUR'",
        "-draw", "text 750,405 '850.00 EUR'",
        "-stroke", "#e2e8f0", "-strokewidth", "1",
        "-draw", "line 50,425 850,425",
        "-stroke", "none",

        # Riga 2
        "-draw", "text 70,460 'NVMe PCIe 4.0 2TB High Endurance'",
        "-draw", "text 530,460 '2'",
        "-draw", "text 630,460 '150.00 EUR'",
        "-draw", "text 750,460 '300.00 EUR'",
        "-stroke", "#e2e8f0", "-strokewidth", "1",
        "-draw", "line 50,480 850,480",
        "-stroke", "none",

        # Riga 3
        "-draw", "text 70,515 'Cavo DAC SFP+ 10G 1 metro'",
        "-draw", "text 530,515 '2'",
        "-draw", "text 640,515 '25.00 EUR'",
        "-draw", "text 760,515 '50.00 EUR'",
        "-stroke", "#e2e8f0", "-strokewidth", "1",
        "-draw", "line 50,535 850,535",
        "-stroke", "none",

        # Box Totale
        "-fill", "#f8fafc", "-stroke", "#cbd5e1", "-strokewidth", "1",
        "-draw", "roundrectangle 500,580 850,720 5,5",
        "-stroke", "none",
        "-pointsize", "15", "-fill", "#475569",
        "-draw", "text 520,615 'Imponibile Netto:'",
        "-draw", "text 740,615 '1200.00 EUR'",
        "-draw", "text 520,650 'IVA 22%:'",
        "-draw", "text 750,650 '264.00 EUR'",
        "-stroke", "#94a3b8", "-strokewidth", "1",
        "-draw", "line 520,670 830,670",
        "-stroke", "none",
        "-pointsize", "20", "-fill", "#0369a1",
        "-draw", "text 520,705 'Totale Euro:'",
        "-draw", "text 720,705 '1464.00 EUR'",

        # Note
        "-pointsize", "13", "-fill", "#64748b",
        "-draw", "text 50,800 'Bonifico Bancario a vista fattura - IBAN: IT60X0542811101000000123456'",
        "-draw", "text 50,825 'Grazie per aver scelto i nostri servizi.'",

        png_path
    ]
    subprocess.run(cmd, check=True)
    print(f"Generato con successo: {png_path}")

def generate_ricevuta():
    jpg_path = os.path.join(FIXTURES_DIR, "ricevuta_test.jpg")
    cmd = [
        "magick",
        "-size", "600x850",
        "xc:#fffbeb",
        "-font", FONT,

        # Intestazione Scontrino
        "-pointsize", "22", "-fill", "#1c1917",
        "-draw", "text 170,60 'CAFFETTERIA & BISTROT'",
        "-pointsize", "14", "-fill", "#44403c",
        "-draw", "text 160,90 'PIAZZA DEL MERCATO 12 - ROMA'",
        "-draw", "text 210,110 'P.IVA 09876543211'",
        "-pointsize", "16", "-fill", "#1c1917",
        "-draw", "text 175,145 'DOCUMENTO COMMERCIALE'",

        # Divisorio
        "-pointsize", "14", "-fill", "#78716c",
        "-draw", "text 50,175 '------------------------------------------------'",
        "-pointsize", "14", "-fill", "#292524",
        "-draw", "text 50,200 '11/10/2026 13:45'",
        "-draw", "text 430,200 'DOC N. 0412'",
        "-pointsize", "14", "-fill", "#78716c",
        "-draw", "text 50,225 '------------------------------------------------'",

        # Voci
        "-pointsize", "15", "-fill", "#1c1917",
        "-draw", "text 50,265 '1 CAFFE ESPRESSO'",
        "-draw", "text 480,265 '1.30 EUR'",
        "-draw", "text 50,305 '2 BRIOCHE ARTIGIANALI'",
        "-draw", "text 480,305 '3.40 EUR'",
        "-draw", "text 50,345 '1 SPREMUTA D ARANCIA'",
        "-draw", "text 480,345 '4.00 EUR'",

        # Totale
        "-pointsize", "14", "-fill", "#78716c",
        "-draw", "text 50,390 '================================================'",
        "-pointsize", "20", "-fill", "#1c1917",
        "-draw", "text 50,430 'TOTALE COMPLESSIVO'",
        "-draw", "text 460,430 '8.70 EUR'",
        "-pointsize", "14", "-fill", "#44403c",
        "-draw", "text 50,470 'PAGAMENTO ELETTRONICO (POS)'",
        "-draw", "text 480,470 '8.70 EUR'",
        "-pointsize", "14", "-fill", "#78716c",
        "-draw", "text 50,510 '------------------------------------------------'",
        "-pointsize", "14", "-fill", "#292524",
        "-draw", "text 210,550 'ARRIVEDERCI E GRAZIE'",
        "-pointsize", "12", "-fill", "#78716c",
        "-draw", "text 190,575 'RT MATRICOLA 99MEC87654'",

        jpg_path
    ]
    subprocess.run(cmd, check=True)
    print(f"Generato con successo: {jpg_path}")

if __name__ == "__main__":
    generate_fattura()
    generate_ricevuta()
