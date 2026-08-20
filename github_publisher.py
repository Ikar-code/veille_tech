# ============================================================
# GITHUB_PUBLISHER.PY — Publication RSS et HTML sur GitHub
# ============================================================
# L'utilisateur renseigne ses infos GitHub dans l'app Render.
# Elles sont stockées en Supabase (config_utilisateur).
# Le cron les récupère et pousse dans le repo GitHub du client.
#
# Comportement dossier rss/ :
#   - Existe déjà → ajoute le fichier dedans
#   - N'existe pas → GitHub le crée automatiquement au push
#
# Comportement dossier docs/ :
#   - Existe déjà → met à jour docs/veille-ia.html
#   - N'existe pas → GitHub le crée automatiquement au push
# ============================================================

import os
import base64
import requests
from datetime import datetime

GITHUB_API = "https://api.github.com"


def _headers(token: str) -> dict:
    return {
        "Authorization":        f"Bearer {token}",
        "Accept":               "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _get_sha(token: str, repo: str, chemin: str):
    """
    Recupere le SHA d'un fichier existant.
    Necessaire uniquement pour mettre a jour un fichier deja present.
    Retourne None si le fichier n'existe pas encore.
    """
    url = f"{GITHUB_API}/repos/{repo}/contents/{chemin}"
    try:
        r = requests.get(url, headers=_headers(token), timeout=10)
        if r.status_code == 200:
            return r.json().get("sha")
    except Exception:
        pass
    return None


def _push_fichier(token: str, repo: str, chemin: str,
                  contenu: str, message_commit: str):
    """
    Cree ou met a jour un fichier dans le repo GitHub.
    Si le dossier parent n'existe pas, GitHub le cree automatiquement.

    token          : Personal Access Token GitHub de l'utilisateur
    repo           : ex: 'Ikar-code/veille_tech'
    chemin         : chemin relatif ex: 'rss/2026-06-12_10-00_ia.xml'
    contenu        : texte brut du fichier
    message_commit : message du commit Git
    """
    if not token or not repo:
        return False, "Token GitHub ou nom du repo manquant"

    url     = f"{GITHUB_API}/repos/{repo}/contents/{chemin}"
    encoded = base64.b64encode(contenu.encode("utf-8")).decode("ascii")
    sha     = _get_sha(token, repo, chemin)

    payload = {
        "message": message_commit,
        "content": encoded,
    }
    if sha:
        payload["sha"] = sha  # Fichier existant -> mise a jour

    try:
        r = requests.put(url, headers=_headers(token), json=payload, timeout=20)
        if r.status_code in (200, 201):
            return True, f"GitHub OK -> {chemin}"
        try:
            detail = r.json().get("message", "?")
        except Exception:
            detail = r.text[:100]
        return False, f"GitHub erreur {r.status_code} : {detail}"
    except Exception as e:
        return False, f"GitHub exception : {e}"


# ============================================================
# GENERATION RSS
# ============================================================

def generer_rss(sujet: str, articles: list, repo: str = "") -> str:
    """Genere un flux RSS 2.0 a partir des articles de la veille."""
    now_rfc   = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")
    lien_repo = f"https://github.com/{repo}" if repo else "https://github.com"

    def _escape(s: str) -> str:
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    items = ""
    for a in articles[:20]:
        titre = _escape(a.get("title", ""))
        lien  = a.get("href", "")
        pts   = a.get("resume_ollama", [])
        desc  = (
            " ".join(pts[:3])
            if pts and pts not in [
                ["Contenu non accessible pour ce site."],
                ["Resume non disponible."]
            ]
            else a.get("body", "")[:200]
        )
        desc = _escape(desc)
        items += f"""
  <item>
    <title>{titre}</title>
    <link>{lien}</link>
    <description>{desc}</description>
    <pubDate>{now_rfc}</pubDate>
    <guid isPermaLink="true">{lien}</guid>
  </item>"""

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Veille IA - {_escape(sujet.title())}</title>
    <link>{lien_repo}</link>
    <description>Veille technologique automatisee sur : {_escape(sujet)}</description>
    <language>fr</language>
    <lastBuildDate>{now_rfc}</lastBuildDate>
    <pubDate>{now_rfc}</pubDate>{items}
  </channel>
</rss>"""


# ============================================================
# FONCTIONS PRINCIPALES
# ============================================================

def publier_rss(token: str, repo: str,
                sujet: str, articles: list):
    """
    Genere et pousse le RSS dans rss/AAAA-MM-JJ_HH-MM_<sujet>.xml
    Le dossier rss/ est cree automatiquement s'il n'existe pas.
    """
    now    = datetime.utcnow()
    slug   = sujet[:20].strip().lower().replace(" ", "-")
    nom    = now.strftime("%Y-%m-%d_%H-%M") + f"_{slug}.xml"
    chemin = f"rss/{nom}"

    contenu = generer_rss(sujet, articles, repo)
    message = f"veille: RSS {sujet[:30]} - {now.strftime('%Y-%m-%d %H:%M')} UTC"

    return _push_fichier(token, repo, chemin, contenu, message)


def publier_html_github_pages(token: str, repo: str, html: str):
    """
    Pousse veille-ia.html dans docs/veille-ia.html.
    Le dossier docs/ est cree automatiquement s'il n'existe pas.
    Accessible via https://<user>.github.io/<repo>/veille-ia.html
    apres activation de GitHub Pages (branche main, dossier /docs).
    """
    now     = datetime.utcnow()
    message = f"veille: HTML - {now.strftime('%Y-%m-%d %H:%M')} UTC"
    return _push_fichier(token, repo, "docs/veille-ia.html", html, message)


def publier_tout(token: str, repo: str,
                 sujet: str, articles: list,
                 html: str = None) -> dict:
    """
    Publie RSS (toujours) + HTML GitHub Pages (si html fourni).

    token    : Personal Access Token GitHub de l'utilisateur
    repo     : 'username/nom-du-repo'  ex: 'Ikar-code/veille_tech'
    sujet    : sujet de la veille
    articles : liste d'articles avec resume_ollama
    html     : contenu HTML complet (optionnel)

    Retourne un dict :
      {
        "rss":          (ok: bool, msg: str),
        "github_pages": (ok: bool, msg: str),  # seulement si html fourni
      }
    """
    resultats = {}

    ok_rss, msg_rss = publier_rss(token, repo, sujet, articles)
    resultats["rss"] = (ok_rss, msg_rss)
    print(f"  [GitHub RSS]  {'OK' if ok_rss else 'ERREUR'} {msg_rss}")

    if html:
        ok_html, msg_html = publier_html_github_pages(token, repo, html)
        resultats["github_pages"] = (ok_html, msg_html)
        print(f"  [GitHub HTML] {'OK' if ok_html else 'ERREUR'} {msg_html}")

    return resultats
