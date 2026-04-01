# ============================================================
# CRON.PY — Veille automatique (GitHub Actions, toutes les heures)
#
# Pour chaque utilisateur programmé à l'heure UTC courante :
#   1. storage.set_user(user_id)       ← OBLIGATOIRE en premier
#   2. srv.set_storage_context(storage) ← OBLIGATOIRE en second
#   3. Charge sa config (FTP, WP, thème) via storage.charger_config()
#   4. Recherche + résumés IA par sujet (srv.workflow_publier)
#      → sauvegarde historique Supabase + publie WP + publie FTP
#   5. Envoie email de synthèse
#   6. Marque la dernière exécution
#
# ROOT CAUSE du bug précédent :
#   charger_config_utilisateur(user_id) ne mettait PAS à jour
#   _current_user_id dans storage.py.
#   Donc storage.charger_historique() lisait _current_user_id=None
#   → retournait {} → workflow_publier ne sauvegardait rien.
#   FIX : toujours appeler storage.set_user(user_id) EN PREMIER.
# ============================================================

import os
import sys
import smtplib
import re
import json
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

GMAIL_USER     = os.environ.get("GMAIL_USER", "")
GMAIL_PASSWORD = os.environ.get("GMAIL_PASSWORD", "")

# ============================================================
# EMAIL HTML
# ============================================================

def generer_email_html(sujets_str: str, articles: list, resume_global: str) -> str:
    date = datetime.now().strftime("%d/%m/%Y")

    resume_html = ""
    for ligne in (resume_global or "").splitlines():
        ligne = ligne.strip()
        if not ligne:
            continue
        ligne = re.sub(r'\*\*', '', ligne)
        if ligne.startswith("—"):
            titre = ligne.lstrip("— ").rstrip(":").strip()
            resume_html += (
                f"<h3 style='color:#1565c0;margin:20px 0 6px 0;font-size:14px;'>"
                f"— {titre}</h3>"
            )
        elif ligne.startswith(("- ", "• ")):
            point = re.sub(r'\s*\[\d+\]', '', ligne.lstrip("-• ").strip())
            resume_html += (
                f"<div style='padding:3px 0 3px 12px;border-left:2px solid #bbdefb;"
                f"margin:3px 0;font-size:13px;'>{point}</div>"
            )
        else:
            resume_html += f"<p style='margin:6px 0;font-size:13px;'>{ligne}</p>"

    articles_html = ""
    for a in articles[:10]:
        dom = urlparse(a.get("href", "")).netloc
        pts = a.get("resume_ollama", [])
        if pts and pts not in [["Contenu non accessible pour ce site."],
                                ["Résumé non disponible."]]:
            pts_li   = "".join(f"<li style='margin:4px 0;color:#444;'>{p}</li>"
                               for p in pts[:3])
            pts_html = (f"<ul style='margin:6px 0 0 0;padding-left:18px;"
                        f"font-size:12px;'>{pts_li}</ul>")
        else:
            pts_html = ""
        articles_html += f"""
        <div style='margin-bottom:14px;padding:12px 14px;background:#f5f7ff;
                    border-radius:6px;border-left:3px solid #1565c0;'>
            <a href='{a.get("href","")}' style='color:#1565c0;font-weight:bold;
               font-size:13px;text-decoration:none;'>{a.get("title","")}</a>
            <div style='font-size:11px;color:#888;margin:3px 0;'>{dom}</div>
            {pts_html}
        </div>"""

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style='font-family:Arial,sans-serif;max-width:680px;margin:0 auto;
             color:#333;background:#f9f9f9;'>
    <div style='background:#1565c0;color:white;padding:24px 28px;
                border-radius:8px 8px 0 0;'>
        <div style='font-size:22px;font-weight:bold;margin-bottom:4px;'>
            🔭 Veille Technologique</div>
        <div style='opacity:.85;font-size:13px;'>{sujets_str} — {date}</div>
    </div>
    <div style='background:white;padding:24px 28px;'>
        <h2 style='color:#1565c0;border-bottom:2px solid #e3f2fd;padding-bottom:8px;
                   font-size:16px;margin-top:0;'>Synthèse</h2>
        {resume_html or "<p style='color:#888;font-style:italic;'>Résumé non disponible.</p>"}
        <h2 style='color:#1565c0;border-bottom:2px solid #e3f2fd;padding-bottom:8px;
                   font-size:16px;margin-top:28px;'>
            Articles ({len(articles)})</h2>
        {articles_html or "<p style='color:#888;font-style:italic;'>Aucun article.</p>"}
    </div>
    <div style='background:#e3f2fd;padding:14px 28px;border-radius:0 0 8px 8px;
                font-size:11px;color:#666;text-align:center;'>
        Veille automatique — {date} · Pour désactiver : onglet Automatisation dans Veille IA
    </div>
</body></html>"""


def envoyer_email(dest: str, sujet_mail: str, html: str) -> bool:
    if not dest or not GMAIL_USER or not GMAIL_PASSWORD:
        print("  ⚠ Email ignoré — GMAIL_USER / GMAIL_PASSWORD non configurés")
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = sujet_mail
        msg["From"]    = GMAIL_USER
        msg["To"]      = dest
        msg.attach(MIMEText(html, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(GMAIL_USER, GMAIL_PASSWORD)
            smtp.sendmail(GMAIL_USER, dest, msg.as_string())
        return True
    except Exception as e:
        print(f"  ✗ Erreur email → {dest} : {e}")
        return False


# ============================================================
# TRAITEMENT D'UN UTILISATEUR
# ============================================================

def traiter_utilisateur(user_id: str, sujets_str: str, email_dest: str):
    print(f"\n  ▶ {email_dest} ({user_id[:8]}…)")

    # ────────────────────────────────────────────────────────
    # ÉTAPE 1 & 2 — OBLIGATOIRES ET EN PREMIER
    # set_user() positionne _current_user_id dans storage.py.
    # Toutes les fonctions storage.charger_*/sauvegarder_* lisent
    # cette variable. Sans ça, elles retournent {} et ne sauvegardent rien.
    # ────────────────────────────────────────────────────────
    storage.set_user(user_id)
    srv.set_storage_context(storage)

    # ÉTAPE 3 — Charge la config via le storage correctement contextualisé
    # On utilise charger_config() (PAS charger_config_utilisateur) car
    # _current_user_id est maintenant positionné.
    cfg = storage.charger_config()

    # Thème personnalisé pour la page FTP
    theme = None
    if "theme_ftp" in cfg:
        try:
            theme = json.loads(cfg["theme_ftp"])
        except Exception:
            theme = None

    sous_sujets    = [s.strip() for s in sujets_str.split(",") if s.strip()]
    articles_email = []
    resumes_email  = []

    for sujet in sous_sujets:
        print(f"    Sujet : «{sujet}»")
        try:
            # ÉTAPE 4a — Recherche
            resultats = srv.rechercher(
                sujet,
                callback_statut=lambda m: print(f"      {m}")
            )
            if not resultats:
                print("      Aucun résultat.")
                continue

            print(f"      {len(resultats)} résultats — publication…")

            # ÉTAPE 4b — workflow_publier
            # Grâce à set_user + set_storage_context fait en amont :
            #   • _charger_historique_ctx() lit bien l'historique Supabase
            #   • _sauvegarder_historique_ctx() écrit bien dans Supabase
            #   • _ftp_config() lit bien la config FTP de l'utilisateur
            res = srv.workflow_publier(
                sujet,
                resultats,
                callback_statut=lambda msg: print(f"      {msg}"),
                limite=int(cfg.get("auto_limite", 10)),
                theme_ftp=theme,
            )

            wp_ok,  wp_msg  = res.get("wordpress", (False, "—"))
            ftp_ok, ftp_msg = res.get("ftp",       (False, "—"))
            print(f"      WP  : {'✓' if wp_ok  else '✗'} {wp_msg}")
            print(f"      FTP : {'✓' if ftp_ok else '✗'} {ftp_msg}")

            # ÉTAPE 5a — Récupère les articles depuis Supabase pour l'email
            # workflow_publier a maintenant sauvegardé → on peut relire
            historique = storage.charger_historique()
            sessions   = historique.get(sujet.strip().lower(), [])
            if sessions and isinstance(sessions[0], dict):
                articles_du_jour = sessions[0].get("articles", [])
                resume_du_jour   = sessions[0].get("resume_global", "")
                articles_email.extend(articles_du_jour[:5])
                if resume_du_jour and not resume_du_jour.startswith("Erreur"):
                    resumes_email.append(
                        f"— {sujet.upper()}\n{resume_du_jour[:800]}"
                    )

            time.sleep(5)

        except Exception as e:
            print(f"      ✗ Erreur : {e}")
            import traceback
            traceback.print_exc()

    # ÉTAPE 6 — Marque la dernière exécution
    storage.marquer_execution(user_id)

    # ÉTAPE 5b — Envoie l'email
    if not articles_email:
        print("    ⚠ Aucun article — email ignoré")
        return

    date       = datetime.now().strftime("%d/%m/%Y")
    resume_all = "\n\n".join(resumes_email) if resumes_email else ""
    html       = generer_email_html(sujets_str, articles_email, resume_all)
    titre_mail = (
        f"Veille IA — {date} · "
        f"{len(articles_email)} article(s) · "
        f"{len(sous_sujets)} sujet(s)"
    )

    ok = envoyer_email(email_dest, titre_mail, html)
    print(f"    Email : {'✓ envoyé' if ok else '✗ ERREUR'} → {email_dest}")


# ============================================================
# MAIN
# ============================================================

def main():
    now_utc = datetime.now(timezone.utc)
    heure   = now_utc.hour
    minute  = 0   # GitHub Actions tourne toutes les heures pile

    print(f"\n{'='*56}")
    print(f"  Cron Veille IA — {now_utc.strftime('%d/%m/%Y %H:%M UTC')}")
    print(f"  Cherche utilisateurs programmés à {heure:02d}h{minute:02d} UTC")
    print(f"{'='*56}")

    if not storage.SUPABASE_OK:
        print("✗ Supabase indisponible — vérifiez SUPABASE_URL / SUPABASE_SERVICE_KEY")
        sys.exit(1)

    utilisateurs = storage.lister_utilisateurs_a_notifier(heure, minute)

    if not utilisateurs:
        print("  Aucun utilisateur programmé à cette heure.")
        return

    print(f"  {len(utilisateurs)} utilisateur(s) à traiter")

    for u in utilisateurs:
        user_id = u.get("user_id", "")
        sujets  = u.get("sujets",  "").strip()
        email   = storage.get_user_email(user_id)

        if not email:
            print(f"  ✗ Email introuvable pour {user_id[:8]}… — ignoré")
            continue
        if not sujets:
            print(f"  ✗ Aucun sujet pour {email} — ignoré")
            continue

        traiter_utilisateur(user_id, sujets, email)

    print(f"\n  Cron terminé — {datetime.now(timezone.utc).strftime('%H:%M UTC')}")
    print(f"{'='*56}\n")


if __name__ == "__main__":
    main()