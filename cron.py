# ============================================================
# CRON.PY — Veille automatique (lancé par Render Cron Job)
# Tourne toutes les heures, envoie les emails aux utilisateurs
# dont l'heure programmée correspond à l'heure actuelle UTC
# ============================================================

import os
import sys
import smtplib
import re
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone
from urllib.parse import urlparse

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

import serveur as srv
import storage

# ============================================================
# CONFIG EMAIL
# ============================================================
GMAIL_USER     = "veille.techno.autobylr@gmail.com"
GMAIL_PASSWORD = os.environ.get("GMAIL_PASSWORD", "pkwe wcbg ntwj sarr")

# ============================================================
# GÉNÉRATION EMAIL HTML
# ============================================================

def generer_email_html(sujet: str, articles: list, resume_global: str) -> str:
    date = datetime.now().strftime("%d/%m/%Y")

    sections_html = ""
    for ligne in (resume_global or "").splitlines():
        ligne = ligne.strip()
        if not ligne:
            continue
        ligne = re.sub(r'\*\*', '', ligne)
        if ligne.startswith("—"):
            titre = ligne.lstrip("— ").strip()
            sections_html += f"<h3 style='color:#1565c0;margin:20px 0 8px 0;'>{titre}</h3>"
        elif ligne.startswith(("- ", "• ")):
            point = re.sub(r'\s*\[\d+\]', '', ligne.lstrip("-• ").strip())
            sections_html += f"<li style='margin:6px 0;line-height:1.6;'>{point}</li>"
        else:
            sections_html += f"<p style='margin:6px 0;'>{ligne}</p>"

    articles_html = ""
    for a in articles[:10]:
        dom    = urlparse(a.get("href","")).netloc
        titre  = a.get("title","")
        lien   = a.get("href","")
        pts    = a.get("resume_ollama", [])
        pts_html = "".join(f"<li>{p}</li>" for p in pts[:3]) if pts else ""
        articles_html += f"""
        <div style='margin-bottom:16px;padding:12px;background:#f5f5f5;border-radius:6px;border-left:3px solid #1565c0;'>
            <a href='{lien}' style='color:#1565c0;font-weight:bold;text-decoration:none;'>{titre}</a>
            <div style='font-size:11px;color:#666;margin:2px 0 6px 0;'>{dom}</div>
            <ul style='margin:0;padding-left:18px;font-size:13px;color:#333;'>{pts_html}</ul>
        </div>"""

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style='font-family:Arial,sans-serif;max-width:700px;margin:0 auto;color:#333;'>
    <div style='background:#1565c0;color:white;padding:24px;border-radius:8px 8px 0 0;'>
        <h1 style='margin:0;font-size:22px;'>Veille Technologique</h1>
        <p style='margin:6px 0 0 0;opacity:.8;'>{sujet.title()} — {date}</p>
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
        Veille automatique générée le {date} — Pour se désabonner, connectez-vous et désactivez la veille auto.
    </div>
</body>
</html>"""

def envoyer_email(email_dest: str, sujet_mail: str, html: str) -> bool:
    if not email_dest:
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = sujet_mail
        msg["From"]    = GMAIL_USER
        msg["To"]      = email_dest
        msg.attach(MIMEText(html, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(GMAIL_USER, GMAIL_PASSWORD)
            smtp.sendmail(GMAIL_USER, email_dest, msg.as_string())
        return True
    except Exception as e:
        print(f"  Erreur email : {e}")
        return False

# ============================================================
# TRAITEMENT D'UN UTILISATEUR
# ============================================================

def traiter_utilisateur(user_id: str, sujets_str: str, email_dest: str):
    print(f"\n  Traitement utilisateur {email_dest}")
    sous_sujets = [s.strip() for s in sujets_str.split(",") if s.strip()]

    # Active le storage pour cet utilisateur
    storage.set_user(user_id)

    # Charge l'historique de cet utilisateur
    historique = storage.charger_historique_utilisateur(user_id)

    for sujet in sous_sujets:
        print(f"    Sujet : {sujet}")
        try:
            # Recherche
            resultats = srv.rechercher(sujet, callback_statut=lambda m: print(f"      {m}"))
            if not resultats:
                print(f"    Aucun résultat pour : {sujet}")
                continue

            # Patch serveur pour cet utilisateur
            srv.charger_historique    = lambda: storage.charger_historique_utilisateur(user_id)
            srv.sauvegarder_historique = lambda h: storage.sauvegarder_historique_utilisateur(user_id, h)

            # Génère résumés + sauvegarde historique
            res = srv.workflow_publier(
                sujet, resultats,
                callback_statut=lambda m: print(f"      {m}"),
                limite=10
            )

            # Récupère les articles et résumé sauvegardés
            historique_frais = storage.charger_historique_utilisateur(user_id)
            sessions = historique_frais.get(sujet.strip().lower(), [])
            articles_email = sessions[0].get("articles", []) if sessions else []
            resume_email   = sessions[0].get("resume_global", "") if sessions else ""

            if not articles_email:
                print(f"    Pas d'articles nouveaux pour : {sujet}")
                continue

            # Envoi email
            date = datetime.now().strftime("%d/%m/%Y")
            html = generer_email_html(sujet, articles_email, resume_email)
            sujet_mail = f"Veille : {sujet.title()} — {date} ({len(articles_email)} articles)"
            ok = envoyer_email(email_dest, sujet_mail, html)
            print(f"    Email {'envoyé' if ok else 'ERREUR'} → {email_dest}")

            time.sleep(5)

        except Exception as e:
            print(f"    Erreur sujet {sujet} : {e}")

    # Marque l'exécution
    storage.marquer_execution(user_id)

# ============================================================
# POINT D'ENTRÉE PRINCIPAL
# ============================================================

def main():
    now_utc = datetime.now(timezone.utc)
    heure   = now_utc.hour
    minute  = 0  # On arrondit à l'heure pile

    print(f"\n{'='*50}")
    print(f"Cron Veille IA — {now_utc.strftime('%d/%m/%Y %H:%M')} UTC")
    print(f"Recherche des utilisateurs programmés à {heure:02d}h{minute:02d} UTC")
    print(f"{'='*50}")

    utilisateurs = storage.lister_utilisateurs_a_notifier(heure, minute)

    if not utilisateurs:
        print("Aucun utilisateur à notifier à cette heure.")
        return

    print(f"{len(utilisateurs)} utilisateur(s) à traiter")

    for u in utilisateurs:
        user_id   = u["user_id"]
        sujets    = u["sujets"]
        email     = storage.get_user_email(user_id)

        if not email:
            print(f"  Email introuvable pour user_id={user_id}, ignoré")
            continue

        traiter_utilisateur(user_id, sujets, email)

    print(f"\nCron terminé.")

if __name__ == "__main__":
    main()