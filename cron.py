# ============================================================
# CRON.PY — Veille automatique (GitHub Actions, toutes les heures)
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

# ============================================================
# IMPORTS AVEC DIAGNOSTIC CLAIR
# ============================================================

_erreurs_import = []

try:
    import serveur as srv
except ImportError as e:
    _erreurs_import.append(f"serveur : {e}")
    srv = None

try:
    import storage
except ImportError as e:
    _erreurs_import.append(f"storage : {e}")
    storage = None

if _erreurs_import:
    print("✗ Erreurs d'import détectées :")
    for err in _erreurs_import:
        print(f"  - {err}")
    print("\nVérifiez que tous les fichiers sont bien présents dans le repo.")
    sys.exit(1)

GMAIL_USER     = os.environ.get("GMAIL_USER", "")
GMAIL_PASSWORD = os.environ.get("GMAIL_PASSWORD", "")

# ============================================================
# VÉRIFICATION DES VARIABLES D'ENVIRONNEMENT
# ============================================================

def verifier_env() -> bool:
    """Vérifie les variables critiques et affiche un diagnostic."""
    manquantes = []

    if not os.environ.get("SUPABASE_URL"):
        manquantes.append("SUPABASE_URL")
    if not os.environ.get("SUPABASE_SERVICE_KEY") and not os.environ.get("SUPABASE_KEY"):
        manquantes.append("SUPABASE_SERVICE_KEY (ou SUPABASE_KEY)")

    if not os.environ.get("GROQ_API_KEY"):
        print("  ⚠ GROQ_API_KEY manquante — résumés IA désactivés")
    if not GMAIL_USER:
        print("  ⚠ GMAIL_USER manquante — emails désactivés")
    if not GMAIL_PASSWORD:
        print("  ⚠ GMAIL_PASSWORD manquante — emails désactivés")

    if manquantes:
        print("✗ Variables d'environnement obligatoires manquantes :")
        for v in manquantes:
            print(f"  - {v}")
        print("\nAjoutez-les dans :")
        print("  GitHub → Settings → Secrets and variables → Actions")
        return False
    return True


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
            resume_html += f"<h3 style='color:#1565c0;margin:20px 0 6px 0;font-size:14px;'>— {titre}</h3>"
        elif ligne.startswith(("- ", "• ")):
            point = re.sub(r'\s*\[\d+\]', '', ligne.lstrip("-• ").strip())
            resume_html += f"<div style='padding:3px 0 3px 12px;border-left:2px solid #bbdefb;margin:3px 0;font-size:13px;'>{point}</div>"
        else:
            resume_html += f"<p style='margin:6px 0;font-size:13px;'>{ligne}</p>"

    articles_html = ""
    for a in articles[:10]:
        dom = urlparse(a.get("href", "")).netloc
        pts = a.get("resume_ollama", [])
        if pts and pts not in [["Contenu non accessible pour ce site."], ["Résumé non disponible."]]:
            pts_li   = "".join(f"<li style='margin:4px 0;color:#444;'>{p}</li>" for p in pts[:3])
            pts_html = f"<ul style='margin:6px 0 0 0;padding-left:18px;font-size:12px;'>{pts_li}</ul>"
        else:
            pts_html = ""
        articles_html += f"""
        <div style='margin-bottom:14px;padding:12px 14px;background:#f5f7ff;border-radius:6px;border-left:3px solid #1565c0;'>
            <a href='{a.get("href","")}' style='color:#1565c0;font-weight:bold;font-size:13px;text-decoration:none;'>{a.get("title","")}</a>
            <div style='font-size:11px;color:#888;margin:3px 0;'>{dom}</div>
            {pts_html}
        </div>"""

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style='font-family:Arial,sans-serif;max-width:680px;margin:0 auto;color:#333;background:#f9f9f9;'>
    <div style='background:#1565c0;color:white;padding:24px 28px;border-radius:8px 8px 0 0;'>
        <div style='font-size:22px;font-weight:bold;margin-bottom:4px;'>🔭 Veille Technologique</div>
        <div style='opacity:.85;font-size:13px;'>{sujets_str} — {date}</div>
    </div>
    <div style='background:white;padding:24px 28px;'>
        <h2 style='color:#1565c0;border-bottom:2px solid #e3f2fd;padding-bottom:8px;font-size:16px;margin-top:0;'>Synthèse</h2>
        {resume_html or "<p style='color:#888;font-style:italic;'>Résumé non disponible.</p>"}
        <h2 style='color:#1565c0;border-bottom:2px solid #e3f2fd;padding-bottom:8px;font-size:16px;margin-top:28px;'>Articles ({len(articles)})</h2>
        {articles_html or "<p style='color:#888;font-style:italic;'>Aucun article.</p>"}
    </div>
    <div style='background:#e3f2fd;padding:14px 28px;border-radius:0 0 8px 8px;font-size:11px;color:#666;text-align:center;'>
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

    # ── 1. Active le storage pour cet utilisateur ──────────────
    storage.set_user(user_id)
    srv.set_storage_context(storage)

    # ── 2. Charge sa config (FTP, WP, thème) ───────────────────
    try:
        cfg = storage.charger_config()
    except Exception as e:
        print(f"  ✗ Impossible de charger la config : {e}")
        cfg = {}

    theme = None
    if "theme_ftp" in cfg:
        try:
            theme = json.loads(cfg["theme_ftp"])
        except Exception:
            theme = None

    sous_sujets    = [s.strip() for s in sujets_str.split(",") if s.strip()]
    articles_email = []
    resumes_email  = []
    date_jour      = datetime.now().strftime("%d/%m/%Y")

    for sujet in sous_sujets:
        print(f"    Sujet : «{sujet}»")
        sujet_lower = sujet.strip().lower()
        try:
            # ── 3. Recherche ──────────────────────────────────────
            resultats = srv.rechercher(sujet, callback_statut=lambda m: print(f"      {m}"))
            if not resultats:
                print("      Aucun résultat.")
                continue

            # ── 4. Résumés IA + sauvegarde historique ─────────────
            limite     = int(cfg.get("auto_limite", 10))
            historique = storage.charger_historique()
            sessions   = historique.get(sujet_lower, [])
            tous_hrefs = {a["href"] for s in sessions for a in s.get("articles", []) if "href" in a}

            nouveaux = []
            for r in resultats:
                href = r.get("href", "")
                if not href or href in tous_hrefs:
                    continue
                if len(nouveaux) >= limite:
                    break
                print(f"      Résumé {len(nouveaux)+1}/{limite} : {r.get('title','')[:45]}…")
                resume = srv.resumer_article_ollama(r.get("title",""), href, r.get("body",""))
                nouveaux.append({
                    "title":          r.get("title", ""),
                    "href":           href,
                    "score":          r.get("score", 0),
                    "resume_ollama":  resume,
                    "date_recherche": date_jour,
                })
                time.sleep(4)

            if not nouveaux:
                print("      Pas de nouveaux articles.")
                continue

            # ── 5. Résumé global ──────────────────────────────────
            print("      Synthèse globale…")
            time.sleep(10)
            resume_global = srv.generer_resume_global(sujet_lower, nouveaux)

            # ── 6. Sauvegarde dans Supabase ───────────────────────
            session_du_jour = next((s for s in sessions if s.get("date") == date_jour), None)
            if session_du_jour:
                session_du_jour["articles"].extend(nouveaux)
                session_du_jour["resume_global"] = resume_global
            else:
                sessions.insert(0, {
                    "date":          date_jour,
                    "articles":      nouveaux,
                    "resume_global": resume_global,
                })
            historique[sujet_lower] = sessions
            storage.sauvegarder_historique(historique)
            print(f"      ✓ {len(nouveaux)} articles sauvegardés dans Supabase")

            # ── 7. Publication WordPress si configuré ─────────────
            if cfg.get("wp_base") and cfg.get("wp_user") and cfg.get("wp_password"):
                try:
                    contenu = srv.generer_contenu_html(historique, date_jour)
                    page_id = srv.obtenir_ou_creer_page()
                    wp_ok, wp_msg = srv.publier_wordpress(contenu, page_id)
                    print(f"      WP  : {'✓' if wp_ok else '✗'} {wp_msg}")
                except Exception as e:
                    print(f"      WP  : ✗ {e}")

            # ── 8. Publication FTP si configuré ───────────────────
            if cfg.get("ftp_host") and cfg.get("ftp_user") and cfg.get("ftp_password"):
                try:
                    ftp_ok, ftp_msg = srv._publier_ftp_avec_historique(None, historique, theme)
                    print(f"      FTP : {'✓' if ftp_ok else '✗'} {ftp_msg}")
                except Exception as e:
                    print(f"      FTP : ✗ {e}")

            # Collecte pour l'email
            articles_email.extend(nouveaux[:5])
            if resume_global and not resume_global.startswith("Erreur"):
                resumes_email.append(f"— {sujet.upper()}\n{resume_global[:800]}")

            time.sleep(5)

        except Exception as e:
            print(f"      ✗ Erreur sujet «{sujet}» : {e}")
            import traceback
            traceback.print_exc()
            # Continue avec le sujet suivant — ne pas planter tout le cron

    # ── 9. Marque l'exécution ─────────────────────────────────
    try:
        storage.marquer_execution(user_id)
    except Exception as e:
        print(f"  ⚠ marquer_execution : {e}")

    # ── 10. Envoi email ───────────────────────────────────────
    if not articles_email:
        print("    ⚠ Aucun article — email ignoré")
        return

    resume_all = "\n\n".join(resumes_email) if resumes_email else ""
    html       = generer_email_html(sujets_str, articles_email, resume_all)
    titre_mail = f"Veille IA — {date_jour} · {len(articles_email)} article(s) · {len(sous_sujets)} sujet(s)"
    ok         = envoyer_email(email_dest, titre_mail, html)
    print(f"    Email : {'✓ envoyé' if ok else '✗ ERREUR'} → {email_dest}")


# ============================================================
# MAIN
# ============================================================

def main():
    now_utc = datetime.now(timezone.utc)
    heure   = now_utc.hour
    minute  = 0

    print(f"\n{'='*56}")
    print(f"  Cron Veille IA — {now_utc.strftime('%d/%m/%Y %H:%M UTC')}")
    print(f"  Utilisateurs programmés à {heure:02d}h{minute:02d} UTC")
    print(f"{'='*56}")

    # ── Vérifie les variables d'environnement ─────────────────
    if not verifier_env():
        sys.exit(1)

    # ── Vérifie Supabase ──────────────────────────────────────
    if not getattr(storage, "SUPABASE_OK", False):
        print("✗ Supabase indisponible — vérifiez SUPABASE_URL / SUPABASE_SERVICE_KEY")
        sys.exit(1)

    print("  ✓ Supabase OK")

    # ── Récupère les utilisateurs à notifier ──────────────────
    try:
        utilisateurs = storage.lister_utilisateurs_a_notifier(heure, minute)
    except Exception as e:
        print(f"✗ Impossible de récupérer les utilisateurs : {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    if not utilisateurs:
        print("  Aucun utilisateur programmé à cette heure.")
        print(f"  (heure UTC actuelle : {heure:02d}h{minute:02d})")
        return

    print(f"  {len(utilisateurs)} utilisateur(s) à traiter")

    nb_ok  = 0
    nb_err = 0

    for u in utilisateurs:
        user_id = u.get("user_id", "")
        sujets  = u.get("sujets", "").strip()

        try:
            email = storage.get_user_email(user_id)
        except Exception as e:
            print(f"  ✗ get_user_email({user_id[:8]}…) : {e}")
            nb_err += 1
            continue

        if not email:
            print(f"  ✗ Email introuvable pour {user_id[:8]}… — ignoré")
            nb_err += 1
            continue
        if not sujets:
            print(f"  ✗ Aucun sujet pour {email} — ignoré")
            nb_err += 1
            continue

        try:
            traiter_utilisateur(user_id, sujets, email)
            nb_ok += 1
        except Exception as e:
            print(f"  ✗ Erreur critique pour {email} : {e}")
            import traceback
            traceback.print_exc()
            nb_err += 1
            # Continue avec l'utilisateur suivant

    print(f"\n  Résumé : {nb_ok} OK, {nb_err} erreur(s)")
    print(f"  Cron terminé — {datetime.now(timezone.utc).strftime('%H:%M UTC')}")
    print(f"{'='*56}\n")


if __name__ == "__main__":
    main()
