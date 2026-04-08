"""
veille_auto.py
Script de veille automatique — lancé par la tâche planifiée Windows.
Lit la configuration depuis config.json et envoie un email de synthèse.
"""
import os
import sys
import json
import smtplib
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from urllib.parse import urlparse

# Chemin racine = dossier parent de .app/
_dir   = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(_dir) if os.path.basename(_dir) == ".app" else _dir
os.chdir(RACINE)
os.environ["VEILLE_RACINE"] = RACINE

sys.path.insert(0, _dir)
import serveur

# Charge la config depuis config.json
_cfg           = serveur.charger_config()
GMAIL_USER     = os.environ.get("GMAIL_USER", _cfg.get("gmail_user", ""))
GMAIL_PASSWORD = os.environ.get("GMAIL_PASSWORD", _cfg.get("gmail_password", ""))
EMAIL_DEST     = _cfg.get("email_dest",    os.environ.get("EMAIL_DEST", ""))
SUJETS         = _cfg.get("email_sujets",  os.environ.get("SUJETS", "intelligence artificielle"))

def generer_email_html(sujet, articles, resume_global):
    date = datetime.now().strftime("%d/%m/%Y")

    sections_html = ""
    for ligne in resume_global.splitlines():
        ligne = ligne.strip()
        if not ligne:
            continue
        ligne = re.sub(r'\*\*', '', ligne)
        if ligne.startswith("—"):
            titre = ligne.lstrip("— ").strip()
            sections_html += f"<h3 style='color:#1565c0;margin:20px 0 8px 0;'>{titre}</h3>"
        elif ligne.startswith(("- ", "• ")):
            point = ligne.lstrip("-• ").strip()
            # Supprime les citations [N] pour l'email
            point = re.sub(r'\s*\[\d+\]', '', point)
            sections_html += f"<li style='margin:6px 0;line-height:1.6;'>{point}</li>"
        else:
            sections_html += f"<p style='margin:6px 0;'>{ligne}</p>"

    articles_html = ""
    for a in articles[:10]:
        dom = urlparse(a.get("href","")).netloc
        titre_art = a.get("title","")
        lien = a.get("href","")
        pts = a.get("resume_ollama", [])
        pts_html = "".join(f"<li>{p}</li>" for p in pts[:3]) if pts else ""
        articles_html += f"""
        <div style='margin-bottom:16px;padding:12px;background:#f5f5f5;border-radius:6px;border-left:3px solid #1565c0;'>
            <a href='{lien}' style='color:#1565c0;font-weight:bold;text-decoration:none;'>{titre_art}</a>
            <div style='font-size:11px;color:#666;margin:2px 0 6px 0;'>{dom}</div>
            <ul style='margin:0;padding-left:18px;font-size:13px;color:#333;'>{pts_html}</ul>
        </div>"""

    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style='font-family:Arial,sans-serif;max-width:700px;margin:0 auto;color:#333;'>
    <div style='background:#1565c0;color:white;padding:24px;border-radius:8px 8px 0 0;'>
        <h1 style='margin:0;font-size:22px;'>Veille Technologique</h1>
        <p style='margin:6px 0 0 0;opacity:0.8;'>{sujet.title()} — {date}</p>
    </div>
    <div style='padding:24px;background:white;'>
        <h2 style='color:#1565c0;border-bottom:2px solid #e0e0e0;padding-bottom:8px;'>Synthèse</h2>
        <ul style='padding-left:18px;'>{sections_html}</ul>
        <h2 style='color:#1565c0;border-bottom:2px solid #e0e0e0;padding-bottom:8px;margin-top:32px;'>
            Top Articles ({len(articles)})
        </h2>
        {articles_html}
    </div>
    <div style='background:#f5f5f5;padding:16px;border-radius:0 0 8px 8px;font-size:11px;color:#999;text-align:center;'>
        Veille automatique générée le {date}
    </div>
</body>
</html>"""

def envoyer_email(sujet_mail, html):
    if not GMAIL_USER or not GMAIL_PASSWORD or not EMAIL_DEST:
        print("Config email manquante")
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = sujet_mail
        msg["From"]    = GMAIL_USER
        msg["To"]      = EMAIL_DEST
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(GMAIL_USER, GMAIL_PASSWORD)
            smtp.sendmail(GMAIL_USER, EMAIL_DEST, msg.as_string())
        print(f"Email envoyé à {EMAIL_DEST}")
        return True
    except Exception as e:
        print(f"Erreur envoi email : {e}")
        return False

def main():
    date = datetime.now().strftime("%d/%m/%Y")
    cfg  = serveur.charger_config()
    sous_sujets = [s.strip() for s in SUJETS.split(",") if s.strip()]
    publier_wp  = cfg.get("auto_publier_wp", True)
    limite      = cfg.get("auto_limite", 15)
    theme_ftp   = None
    if cfg.get("theme_ftp"):
        try:
            theme_ftp = json.loads(cfg["theme_ftp"]) if isinstance(cfg["theme_ftp"], str) else cfg["theme_ftp"]
        except Exception:
            theme_ftp = None

    for sujet in sous_sujets:
        print(f"\n=== Veille : {sujet} ===")

        # Recherche
        print("Recherche en cours...")
        resultats = serveur.rechercher(sujet, callback_statut=lambda m: print(f"  {m}"))
        if not resultats:
            print(f"Aucun résultat pour : {sujet}")
            continue

        print(f"{len(resultats)} résultats trouvés")

        # workflow_publier gère tout : filtre doublons, résumés IA, historique, WP, FTP
        if publier_wp:
            print("Publication WordPress + FTP...")
            res = serveur.workflow_publier(
                sujet,
                resultats,
                callback_statut=lambda msg: print(f"  {msg}"),
                limite=limite,
                theme_ftp=theme_ftp,
            )
            print(f"  WordPress : {res.get('wordpress',(False,'?'))[1]}")
            print(f"  FTP       : {res.get('ftp',(False,'?'))[1]}")

            # Récupère les articles et le résumé sauvegardés dans l'historique
            historique   = serveur.charger_historique()
            sessions     = historique.get(sujet.strip().lower(), [])
            articles_email = sessions[0].get("articles", []) if sessions else []
            resume_email   = sessions[0].get("resume_global", "") if sessions else ""

        else:
            # Sans publication WP — génère résumés manuellement pour l'email
            import time
            sujet_norm = sujet.strip().lower()
            historique = serveur.charger_historique()
            sessions   = historique.get(sujet_norm, [])
            hrefs_vus  = {a["href"] for s in sessions for a in s.get("articles", [])}
            nouveaux   = [r for r in resultats if r.get("href","") not in hrefs_vus][:limite]

            print(f"{len(nouveaux)} nouveaux articles à résumer")
            if not nouveaux:
                print("Aucun nouvel article — email ignoré")
                continue

            articles_email = []
            for i, r in enumerate(nouveaux):
                print(f"Résumé {i+1}/{len(nouveaux)} : {r['title'][:50]}...")
                resume = serveur.resumer_article_ollama(r.get("title",""), r.get("href",""), r.get("body",""))
                articles_email.append({**r, "resume_ollama": resume})
                time.sleep(3)

            print("Synthèse globale...")
            time.sleep(5)
            resume_email = serveur.generer_resume_global(sujet, articles_email)

        # Envoi email
        if EMAIL_DEST and articles_email:
            print("Envoi email...")
            html = generer_email_html(sujet, articles_email, resume_email)
            sujet_mail = f"Veille : {sujet.title()} — {date} ({len(articles_email)} articles)"
            envoyer_email(sujet_mail, html)
        elif not EMAIL_DEST:
            print("Email non configuré — envoi ignoré")
        else:
            print("Aucun nouvel article — email ignoré")

if __name__ == "__main__":
    main()