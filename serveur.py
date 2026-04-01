# ============================================================
# SERVEUR — Logique métier de la veille technologique
# ============================================================

from ddgs import DDGS
from datetime import datetime
import requests
import base64
import json
import re
import os
import unicodedata
import ftplib
import io
from urllib.parse import urlparse
from html.parser import HTMLParser
from difflib import SequenceMatcher

try:
    import feedparser
    FEEDPARSER_OK = True
except ImportError:
    FEEDPARSER_OK = False

import os as _os

def _resoudre_racine():
    env = _os.environ.get("VEILLE_RACINE", "").strip()
    if env and _os.access(env, _os.W_OK):
        return env
    if _os.access("/tmp", _os.W_OK):
        return "/tmp"
    return _os.path.dirname(_os.path.abspath(__file__))

_RACINE = _resoudre_racine()
_APP    = _os.path.join(_RACINE, ".app")
_os.makedirs(_APP, exist_ok=True)

CONFIG_FILE         = _os.path.join(_APP, "config.json")
VEILLE_PAGE_ID_FILE = _os.path.join(_APP, "veille_page_id.json")
HISTORIQUE_FILE     = _os.path.join(_APP, "historique_veille.json")

_storage_context = None

def set_storage_context(ctx):
    global _storage_context
    _storage_context = ctx

def _charger_config_ctx():
    if _storage_context:
        try: return _storage_context.charger_config()
        except Exception: pass
    return charger_config_local()

def _sauvegarder_config_ctx(cfg):
    if _storage_context:
        try: _storage_context.sauvegarder_config(cfg); return
        except Exception: pass
    sauvegarder_config_local(cfg)

def _charger_historique_ctx():
    if _storage_context:
        try: return _storage_context.charger_historique()
        except Exception: pass
    return charger_historique_local()

def _sauvegarder_historique_ctx(h):
    if _storage_context:
        try: _storage_context.sauvegarder_historique(h); return
        except Exception: pass
    sauvegarder_historique_local(h)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

HEADERS_WEB = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
}

DOMAINES_FR_PRIORITAIRES = [
    "lemonde.fr","lefigaro.fr","liberation.fr","20minutes.fr",
    "bfmtv.com","franceinfo.fr","numerama.com","01net.com",
    "futura-sciences.com","journaldunet.com","usine-digitale.fr",
    "latribune.fr","lesechos.fr"
]
DOMAINES_EN_FIABLES = [
    "bbc.com","reuters.com","theguardian.com","techcrunch.com",
    "wired.com","forbes.com","bloomberg.com","nature.com",
    "sciencedirect.com","arxiv.org","mit.edu","stanford.edu",
    "medium.com","towardsdatascience.com"
]
DOMAINES_FAIBLE_QUALITE = [
    "pinterest","reddit","quora","yahoo","forum","amazon",
    "ebay","alibaba","tiktok","instagram","convertflow",
    "commoninja","fouita","jotform","wix.com","squarespace",
    "canva","typeform","surveymonkey","mailchimp"
]
DOMAINES_GOUVERNEMENTAUX_BLOQUES = [
    "securite-civile.interieur.gouv.fr","police-nationale.interieur.gouv.fr",
    "interieur.gouv.fr","education.gouv.fr","sante.gouv.fr",
    "travail.gouv.fr","justice.gouv.fr","defense.gouv.fr",
    "impots.gouv.fr","caf.fr","ameli.fr","securite-sociale.fr",
    "service-public.fr","vie-publique.fr","info.gouv.fr",
    "elysee.fr","premier-ministre.gouv.fr","assemblee-nationale.fr",
    "senat.fr","legifrance.gouv.fr","data.gouv.fr","ansm.sante.fr",
    "inrs.fr","masecurite.fr","securite-routiere.gouv.fr",
]
PATTERNS_GOUVERNEMENTAUX_BLOQUES = [
    "securite-routiere","assr","bsr","permis-conduire",
    "sante-travail","vaccination","vaccin","pharmacovigilance",
    "police-nationale","gendarmerie","pompier","securite-civile",
]
TITRES_HORS_SUJET = [
    "attestation scolaire","sécurité routière","assr","permis de conduire",
    "vaccin","pharmacovigilance","sécurité des patients","sécurité au travail",
    "pression des pneus","tpms","sécurité civile","police nationale",
    "gendarmerie","pompiers","ministère de l'intérieur",
    "sécurité sociale","caf ","impôts","sénat","assemblée nationale",
]
FLUX_RSS_IA = [
    "https://www.usine-digitale.fr/rss/intelligence-artificielle.xml",
    "https://www.numerama.com/tag/intelligence-artificielle/feed/",
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://www.wired.com/feed/category/artificial-intelligence/latest/rss",
    "https://arxiv.org/rss/cs.AI",
    "https://feeds.feedburner.com/TheHackersNews",
]

# ============================================================
# CONFIG
# ============================================================

def charger_config_local():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def sauvegarder_config_local(config: dict):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def charger_config():
    return _charger_config_ctx()

def sauvegarder_config(config: dict):
    _sauvegarder_config_ctx(config)

def tester_connexion_wp(url, user, pwd):
    if not url or not user or not pwd:
        return False, "Remplissez tous les champs WordPress."
    try:
        base = url.rstrip("/")
        if "/wp-json" not in base:
            base += "/wp-json/wp/v2"
        import base64 as b64
        token = b64.b64encode(f"{user}:{pwd}".encode()).decode()
        r = requests.get(f"{base}/users/me",
                         headers={"Authorization": f"Basic {token}"}, timeout=8)
        if r.status_code == 200:
            return True, f"Connexion reussie ! Connecte : {r.json().get('name', user)}"
        elif r.status_code == 401: return False, "Identifiants incorrects."
        elif r.status_code == 403: return False, "Acces refuse."
        elif r.status_code == 404: return False, "URL introuvable."
        else: return False, f"Erreur {r.status_code}."
    except requests.exceptions.ConnectionError:
        est_local = any(x in url.lower() for x in ["localhost", ".local", "127.0.0.1"])
        return False, "Site local inaccessible." if est_local else "Site distant inaccessible."
    except requests.exceptions.Timeout:
        return False, "Delai depasse."
    except Exception as e:
        return False, f"Erreur : {e}"

def tester_connexion_ftp(host, user, pwd):
    if not host or not user or not pwd:
        return False, "Remplissez tous les champs FTP."
    try:
        ftp = ftplib.FTP()
        ftp.connect(host, 21, timeout=10)
        ftp.login(user, pwd)
        ftp.quit()
        return True, f"Connexion FTP reussie sur {host} !"
    except ftplib.error_perm:
        return False, "Identifiants FTP incorrects."
    except Exception as e:
        return False, f"Erreur FTP : {e}"

def config_existe():
    config = charger_config()
    return bool(config.get("wp_base") and config.get("wp_user") and config.get("wp_password"))

def _ftp_config():
    config = charger_config()
    return {
        "host":     config.get("ftp_host", ""),
        "user":     config.get("ftp_user", ""),
        "password": config.get("ftp_password", ""),
        "path":     config.get("ftp_path", "/htdocs/veille-ia.html"),
    }

def ftp_est_configure():
    cfg = _ftp_config()
    placeholders = {"", "if0_xxxxxxx", "xxxx xxxx xxxx", "votre mot de passe ftp"}
    host = cfg["host"].strip().lower()
    user = cfg["user"].strip().lower()
    pwd  = cfg["password"].strip().lower()
    return (bool(host) and host not in placeholders and
            bool(user) and user not in placeholders and
            bool(pwd)  and pwd  not in placeholders)

# ============================================================
# WORDPRESS
# ============================================================

def _get_wp_headers():
    config = charger_config()
    user  = config.get("wp_user", "")
    pwd   = config.get("wp_password", "")
    token = base64.b64encode(f"{user}:{pwd}".encode()).decode("utf-8")
    return {"Authorization": f"Basic {token}", "Content-Type": "application/json"}

def _wp_base():
    base = charger_config().get("wp_base", "").rstrip("/")
    if not base:
        return ""
    if "/wp-json" not in base:
        base += "/wp-json/wp/v2"
    return base

def obtenir_ou_creer_page():
    try:
        with open(VEILLE_PAGE_ID_FILE, "r") as f:
            pid = json.load(f).get("id")
            if pid:
                return pid
    except Exception:
        pass
    base = _wp_base()
    if not base:
        return None
    try:
        r = requests.get(f"{base}/pages?search=Veille+IA&per_page=10",
                         headers=_get_wp_headers(), timeout=10)
        pages = r.json() if r.status_code == 200 else []
        if not isinstance(pages, list):
            pages = []
        for page in pages:
            if "veille ia" in page.get("title", {}).get("rendered", "").lower():
                pid = page["id"]
                with open(VEILLE_PAGE_ID_FILE, "w") as f:
                    json.dump({"id": pid}, f)
                return pid
        r = requests.post(f"{base}/pages", headers=_get_wp_headers(), json={
            "title": "Veille Technologique",
            "content": "<p>Les résultats apparaîtront ici.</p>",
            "status": "publish", "slug": "veille-ia"
        }, timeout=10)
        if r.status_code in [200, 201]:
            pid = r.json()["id"]
            with open(VEILLE_PAGE_ID_FILE, "w") as f:
                json.dump({"id": pid}, f)
            return pid
    except Exception as e:
        print(f"[WP] Erreur page : {e}")
    return None

# ============================================================
# UTILITAIRES
# ============================================================

def normaliser(texte):
    if not texte:
        return ""
    texte = texte.lower()
    return ''.join(
        c for c in unicodedata.normalize('NFD', texte)
        if unicodedata.category(c) != 'Mn'
    )

def est_bloque(r, sujet=""):
    url   = r.get("href", "")
    titre = normaliser(r.get("title", ""))
    body  = normaliser(r.get("body", ""))
    dom   = urlparse(url).netloc.lower()
    if any(d in dom for d in DOMAINES_GOUVERNEMENTAUX_BLOQUES):
        return True
    if any(p in normaliser(url) for p in PATTERNS_GOUVERNEMENTAUX_BLOQUES):
        return True
    if any(t in titre for t in TITRES_HORS_SUJET):
        return True
    if sujet:
        mots_sujet = [m for m in re.split(r"[,\s]+", normaliser(sujet)) if len(m) > 2]
        texte = titre + " " + body
        if mots_sujet and not any(m in texte for m in mots_sujet):
            return True
    return False

def deduplique_semantique(liste, seuil=0.75):
    uniques, titres_vus = [], []
    for r in liste:
        titre = normaliser(r.get("title", ""))
        if not any(SequenceMatcher(None, titre, t).ratio() > seuil for t in titres_vus):
            uniques.append(r)
            titres_vus.append(titre)
    return uniques

def detecter_doublons_contenu(nouveaux_articles, sessions_existantes, seuil=0.70):
    resumes_existants = []
    for s in sessions_existantes:
        for a in s.get("articles", []):
            pts = a.get("resume_ollama", [])
            if pts and pts != ["Contenu non accessible pour ce site."]:
                resumes_existants.append((" ".join(pts).lower(), a.get("title", ""), a.get("href", "")))
    for article in nouveaux_articles:
        pts = article.get("resume_ollama", [])
        if not pts or pts == ["Contenu non accessible pour ce site."]:
            continue
        texte_nouveau = " ".join(pts).lower()
        for texte_ancien, titre_ancien, _ in resumes_existants:
            if SequenceMatcher(None, texte_nouveau, texte_ancien).ratio() > seuil:
                article["doublon_de"] = titre_ancien[:60]
                break
    return nouveaux_articles

# ============================================================
# EXTRACTION DE TEXTE
# ============================================================

class ExtracteurTexte(HTMLParser):
    BALISES_IGNOREES = {"script","style","nav","footer","header","aside",
                        "noscript","iframe","form","button","input","meta",
                        "select","option","label","figure","figcaption"}
    def __init__(self):
        super().__init__()
        self.texte = []
        self._ignorer = 0
    def handle_starttag(self, tag, attrs):
        if tag.lower() in self.BALISES_IGNOREES:
            self._ignorer += 1
    def handle_endtag(self, tag):
        if tag.lower() in self.BALISES_IGNOREES:
            self._ignorer = max(0, self._ignorer - 1)
    def handle_data(self, data):
        if self._ignorer == 0:
            t = data.strip()
            if len(t) > 15:
                self.texte.append(t)
    def get_texte(self):
        return ' '.join(self.texte)

def extraire_texte_page(url):
    try:
        from newspaper import Article
        a = Article(url, language='fr')
        a.download()
        a.parse()
        t = a.text.strip()
        if len(t) > 200:
            return t
    except Exception:
        pass
    try:
        headers = {**HEADERS_WEB, "Accept-Encoding": "identity"}
        resp = requests.get(url, headers=headers, timeout=12)
        enc  = resp.apparent_encoding or resp.encoding or "utf-8"
        html = resp.content.decode(enc, errors="replace")
        if "<html" not in html.lower():
            return ""
        if html.count('\ufffd') > len(html) * 0.05:
            return ""
        p = ExtracteurTexte()
        p.feed(html)
        return re.sub(r'\s{2,}', ' ', p.get_texte()).strip()
    except Exception:
        return ""

# ============================================================
# SCORING
# ============================================================

def scorer_resultat(r, sujet):
    score = 0
    url   = r.get("href", "")
    titre = r.get("title", "")
    body  = r.get("body", "")
    dom   = urlparse(url).netloc.lower()
    tn    = normaliser(titre)
    bn    = normaliser(body)

    if any(d in dom for d in DOMAINES_FR_PRIORITAIRES):  score += 50
    elif dom.endswith(".fr"):                             score += 30
    elif any(d in dom for d in DOMAINES_EN_FIABLES):     score += 20
    elif dom.endswith(".com") or dom.endswith(".org"):    score += 10

    if any(d in dom for d in DOMAINES_FAIBLE_QUALITE): score -= 80

    mots_bloques = ["dictionnaire","definition","lexique","glossaire","encyclopedie"]
    if any(m in tn for m in mots_bloques): score -= 100

    mots_fr = ["les","des","est","aux","que","qui","sur","pour","avec","dans",
               "une","du","au","par","son","ses","ils","elle","nous","vous"]
    mots_en = ["the","of","and","to","in","is","that","was","for","are",
               "with","they","this","from","have","been","will","not","but"]
    mots_autres = [" el "," los "," las "," del "," con "," por "," para ",
                   " como "," este "," esta "," pero "," sin "," sobre ",
                   " em "," no "," se "," ao "," da "," um "," sua ",
                   " il "," di "," che "," non "," per "," degli "]
    td = " " + tn + " " + bn[:300] + " "
    sf = sum(1 for m in mots_fr if f" {m} " in td)
    se = sum(1 for m in mots_en if f" {m} " in td)
    sa = sum(1 for m in mots_autres if m in td)
    est_fr    = sf >= 2
    est_en    = se >= 2
    est_autre = sa >= 3 and not est_fr and not est_en
    if est_autre:                   score -= 200
    elif not est_fr and not est_en: score -= 80

    for mot in re.split(r"[,\s]+", normaliser(sujet)):
        mot = mot.strip()
        if len(mot) > 2:
            if mot in tn: score += 25
            if mot in bn: score += 10

    mots_cles_ia = [
        "intelligence artificielle","machine learning","deep learning",
        "ia generative","large language model","chatgpt","algorithme",
        "automatisation","deepfake","biais algorithme","cybersecurite",
        "attaque adversariale","menace numerique","vulnerabilite ia",
        "securite des modeles","prompt injection","desinformation",
        "bot malveillant","vie privee","rgpd","ethique ia","regulation ia",
        "ai act europe","conformite ia","iot","objets connectes",
        "internet des objets","reseau neuronal","traitement langage naturel"
    ]
    for m in mots_cles_ia:
        if m in tn: score += 15
        if m in bn: score += 5

    annee = str(datetime.now().year)
    if annee in body or annee in titre: score += 10
    if len(body) > 300: score += 10
    elif len(body) > 100: score += 5

    r["score"] = score
    return r

# ============================================================
# RÉSUMÉS IA (Groq)
# ============================================================

def resumer_article_ollama(titre, url, body_ddg):
    if not GROQ_API_KEY:
        return _resumer_fallback(body_ddg)
    texte  = extraire_texte_page(url)
    source = texte if len(texte) > 300 else body_ddg
    if not source or len(source.strip()) < 60:
        return ["Contenu non accessible pour ce site."]
    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}",
                     "Content-Type": "application/json"},
            json={
                "model": "llama-3.1-8b-instant",
                "max_tokens": 300,
                "messages": [
                    {"role": "system",
                     "content": "Tu es un assistant de veille technologique. Tu résumes des articles en 3 à 5 points clés, en français, de manière concrète et factuelle."},
                    {"role": "user",
                     "content": f"Article : \"{titre}\"\n\nContenu :\n{source[:2500]}\n\nRédige 3 à 5 points clés. Chaque point commence par \"• \". Phrases complètes. Uniquement les points."}
                ]
            }, timeout=30
        )
        if resp.status_code == 200:
            contenu = resp.json()["choices"][0]["message"]["content"].strip()
            points  = [l.lstrip("•-–* ").strip()
                       for l in contenu.splitlines()
                       if l.strip() and l.strip()[0] in "•-–*" and len(l.strip()) > 30]
            if points:
                return points[:5]
            phrases = re.split(r'(?<=[.!?])\s+', contenu)
            phrases = [p.strip() for p in phrases if len(p.strip()) > 40]
            return phrases[:5] if phrases else [contenu[:400]]
        return _resumer_fallback(source)
    except Exception:
        return _resumer_fallback(source)

def _resumer_fallback(source):
    if not source:
        return ["Résumé non disponible."]
    phrases = re.split(r'(?<=[.!?])\s+', source)
    phrases = [p.strip() for p in phrases if 50 < len(p.strip()) < 400]
    return phrases[:4] if phrases else ["Résumé non disponible."]

# ============================================================
# RÉSUMÉ GLOBAL (Groq)
# ============================================================

def generer_resume_global(sujet, articles):
    if not articles:
        return "Aucun article analysé."
    if not GROQ_API_KEY:
        return "Clé API Groq manquante (variable GROQ_API_KEY)."
    contexte = ""
    for i, a in enumerate(articles[:12]):
        titre  = a.get("title", "")
        dom    = urlparse(a.get("href", "")).netloc
        points = a.get("resume_ollama", [])
        inacc  = not points or points in [["Contenu non accessible pour ce site."], ["Résumé non disponible."]]
        if not inacc:
            contexte += f"\n[{i+1}] {titre} ({dom})\n"
            for p in points[:3]:
                contexte += f"  - {p}\n"
        else:
            body = a.get("body", "").strip()
            if body and len(body) > 40:
                contexte += f"\n[{i+1}] {titre} ({dom})\n  - {body[:300]}\n"
    if not contexte.strip():
        return "Impossible de générer un résumé global."
    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}",
                     "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "max_tokens": 3000,
                "messages": [
                    {"role": "system",
                     "content": ("Tu es un analyste en veille technologique. "
                                 "Tu rédiges des synthèses concrètes en français. "
                                 "JAMAIS de participe présent (-ant). JAMAIS de généralités. "
                                 "Quand tu utilises une info d'un article, ajoute [N] à la fin.")},
                    {"role": "user",
                     "content": f"""Voici les résumés de {len(articles)} articles sur : "{sujet}"

{contexte}

RÈGLES : cite chaque source {", ".join(f"[{i+1}]" for i in range(min(len(articles),12)))} au moins une fois.

Format :
— Menaces & risques identifiés
- [fait] [N]

— Comment se protéger
- [conseil] [N]

— Outils & technologies
- [outil] [N]

— Tendances à surveiller
- [tendance] [N]

Phrases directes. N'invente rien."""}
                ]
            }, timeout=30
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"].strip()
        elif resp.status_code == 429:
            import time
            time.sleep(30)
            resp2 = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}",
                         "Content-Type": "application/json"},
                json={"model": "llama-3.3-70b-versatile", "max_tokens": 3000,
                      "messages": [{"role": "user", "content": contexte[:2000]}]},
                timeout=30
            )
            if resp2.status_code == 200:
                return resp2.json()["choices"][0]["message"]["content"].strip()
        return f"Erreur Groq ({resp.status_code})"
    except Exception as e:
        return f"Erreur résumé global : {e}"

# ============================================================
# HISTORIQUE
# ============================================================

def charger_historique_local():
    try:
        with open(HISTORIQUE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def sauvegarder_historique_local(h):
    with open(HISTORIQUE_FILE, "w", encoding="utf-8") as f:
        json.dump(h, f, ensure_ascii=False, indent=2)

def charger_historique():
    return _charger_historique_ctx()

def sauvegarder_historique(h):
    _sauvegarder_historique_ctx(h)

def effacer_historique():
    _sauvegarder_historique_ctx({})

def comparer_sessions(sujet, session_nouvelle, session_ancienne):
    date_new      = session_nouvelle.get("date", "récente")
    date_old      = session_ancienne.get("date", "précédente")
    hrefs_anciens = {a["href"] for a in session_ancienne.get("articles", []) if "href" in a}
    nouveaux      = [a for a in session_nouvelle.get("articles", []) if a.get("href") and a["href"] not in hrefs_anciens]
    hrefs_nouveaux = {a["href"] for a in session_nouvelle.get("articles", []) if "href" in a}
    disparus      = [a for a in session_ancienne.get("articles", []) if a.get("href") and a["href"] not in hrefs_nouveaux]
    if not nouveaux and not disparus:
        return f"Aucune différence entre les sessions du {date_old} et du {date_new}."
    contexte = (f"Session précédente : {date_old} ({len(session_ancienne.get('articles') or [])} articles)\n"
                f"Session récente : {date_new} ({len(session_nouvelle.get('articles') or [])} articles)\n\n")
    if nouveaux:
        contexte += f"NOUVEAUX ARTICLES ({len(nouveaux)}) :\n"
        for a in nouveaux[:6]:
            pts = a.get("resume_ollama", [])
            contexte += f"- {a.get('title', '')}\n"
            if pts and pts != ["Contenu non accessible pour ce site."]:
                for p in pts[:2]:
                    contexte += f"  · {p}\n"
    if disparus:
        contexte += f"\nARTICLES DISPARUS ({len(disparus)}) :\n"
        for a in disparus[:4]:
            contexte += f"- {a.get('title', '')}\n"
    if not GROQ_API_KEY:
        return contexte
    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}",
                     "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "max_tokens": 1000,
                "messages": [
                    {"role": "system", "content": "Tu compares deux sessions de veille technologique."},
                    {"role": "user", "content": f"Sujet : \"{sujet}\"\n\n{contexte}\n\nRédige un résumé des évolutions."}
                ]
            }, timeout=30
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"].strip()
        return f"Erreur Groq ({resp.status_code})"
    except Exception as e:
        return f"Erreur : {e}"

# ============================================================
# RECHERCHE PRINCIPALE
# ============================================================

def rechercher(sujet_brut, callback_statut=None):
    def statut(msg):
        if callback_statut:
            callback_statut(msg)

    sous_sujets = [s.strip() for s in sujet_brut.split(",") if s.strip()]
    data, ids_vus = [], set()

    statut("Recherche DuckDuckGo...")
    import warnings
    warnings.filterwarnings("ignore")
    try:
        with DDGS() as ddgs:
            for ss in sous_sujets:
                queries = [
                    ss + " intelligence artificielle actualite",
                    ss + " IA " + str(datetime.now().year),
                    ss + " artificial intelligence"
                ]
                for q in queries:
                    for r in (ddgs.text(q, region="fr-fr", max_results=25) or []):
                        lien = r.get("href", "#")
                        if lien not in ids_vus:
                            ids_vus.add(lien)
                            r["sous_sujet"] = ss
                            data.append(r)
    except Exception as e:
        statut(f"DuckDuckGo : {e}")

    statut("Recuperation flux RSS...")
    if FEEDPARSER_OK:
        mots = [normaliser(m) for m in re.split(r"[,\s]+", sujet_brut) if len(m) > 2]
        for url_flux in FLUX_RSS_IA:
            try:
                feed = feedparser.parse(url_flux)
                for entry in feed.entries[:20]:
                    lien  = entry.get("link", "")
                    titre = entry.get("title", "")
                    body  = entry.get("summary", "")
                    if not lien or lien in ids_vus:
                        continue
                    tn = normaliser(titre)
                    bn = normaliser(body)
                    if any(m in tn or m in bn for m in mots):
                        ids_vus.add(lien)
                        data.append({"title": titre, "body": body, "href": lien, "source": "rss"})
            except Exception:
                continue

    statut("Filtrage et scoring...")
    data = [r for r in data if not est_bloque(r, sujet_brut)]
    data = [scorer_resultat(r, sujet_brut) for r in data]
    data.sort(key=lambda x: x["score"], reverse=True)
    data = deduplique_semantique(data)
    filtres = [r for r in data if r["score"] >= 50]
    if not filtres:
        filtres = [r for r in data if r["score"] >= 35]
    filtres = filtres[:50]
    statut(f"{len(filtres)} resultats trouves")
    return filtres

# ============================================================
# GÉNÉRATION HTML
# ============================================================

def _formater_resume_html(texte, articles_ref):
    if not texte:
        return ""
    index_urls = {i+1: (a.get("href", ""), urlparse(a.get("href", "")).netloc)
                  for i, a in enumerate(articles_ref[:12])}

    def remplacer_citation(m):
        num = int(m.group(1))
        if num in index_urls:
            url_r, dom_r = index_urls[num]
            return (f' <a href="{url_r}" target="_blank" '
                    f'style="color:#89b4fa;font-size:11px;text-decoration:none;" '
                    f'title="{dom_r}">[{num}]</a>')
        return m.group(0)

    html = ""
    for ligne in texte.splitlines():
        ligne = ligne.strip()
        if not ligne:
            continue
        ligne = re.sub(r'\*\*', '', ligne).strip()
        if ligne.startswith("—") and len(ligne) > 2:
            titre = ligne.lstrip("— ").rstrip(": ").strip()
            html += f"<div style='font-size:13px;font-weight:bold;color:#f9e2af;margin:14px 0 6px 0;'>— {titre}</div>"
        elif ligne.startswith("##"):
            titre = ligne.lstrip("# ").rstrip(": ").strip()
            html += f"<div style='font-size:13px;font-weight:bold;color:#f9e2af;margin:14px 0 6px 0;'>— {titre}</div>"
        elif ligne.startswith(("- ", "* ", "• ")):
            point = re.sub(r'\*\*', '', ligne.lstrip("-*• ").strip())
            point = point.replace("<", "&lt;").replace(">", "&gt;")
            point = re.sub(r'\[(\d+)\]', remplacer_citation, point)
            html += f"<div style='padding:3px 0 3px 14px;border-left:2px solid #45475a;margin:3px 0;line-height:1.6;'>{point}</div>"
        else:
            ligne = re.sub(r'\*\*', '', ligne).replace("<", "&lt;").replace(">", "&gt;")
            ligne = re.sub(r'\[(\d+)\]', remplacer_citation, ligne)
            html += f"<p style='margin:6px 0;line-height:1.7;'>{ligne}</p>"
    return html

def generer_bloc_mot_cle(mot_cle, articles, tab_id, resume_global_texte="", date_session="", badge=""):
    date_affichee = date_session or (articles[0].get("date_recherche", "N/A") if articles else "N/A")
    lignes_tableau = ""
    for a in articles:
        dom    = urlparse(a.get("href", "")).netloc
        langue = "FR" if dom.endswith(".fr") or any(d in dom for d in DOMAINES_FR_PRIORITAIRES) else "EN"
        points = a.get("resume_ollama", [])
        if points and points not in [["Contenu non accessible pour ce site."], ["Résumé non disponible."]]:
            html_pts = "<ul style='margin:6px 0 0 0;padding-left:18px;'>"
            for pt in points:
                pt_s = pt.replace("<", "&lt;").replace(">", "&gt;")
                html_pts += f"<li style='margin:4px 0;font-size:12px;color:#6c7086;line-height:1.6;'>{pt_s}</li>"
            html_pts += "</ul>"
        else:
            html_pts = "<div style='font-size:12px;color:#6c7086;margin-top:4px;font-style:italic;'>Résumé non disponible.</div>"
        doublon       = a.get("doublon_de", "")
        badge_doublon = ("<span style='background:#f9e2af;color:#1e1e2e;font-size:10px;padding:2px 6px;border-radius:8px;margin-left:6px;'>~ doublon</span>" if doublon else "")
        lignes_tableau += f"""
        <tr>
            <td style="padding:8px;text-align:center;vertical-align:top;">{langue}</td>
            <td style="padding:8px;vertical-align:top;"><strong>{a.get('title','')}</strong>{badge_doublon}{html_pts}</td>
            <td style="padding:8px;text-align:center;vertical-align:top;white-space:nowrap;">
                <a href="{a.get('href','#')}" style="color:#89b4fa;" target="_blank">ouvrir</a>
            </td>
        </tr>"""
    section_resume = ""
    if resume_global_texte:
        html_r = _formater_resume_html(resume_global_texte, articles)
        section_resume = f"""
        <div style="margin-top:18px;padding:18px;background:linear-gradient(135deg,#1e1e2e,#2a2a3e);border-left:4px solid #f9e2af;border-radius:8px;">
            <div style="font-size:14px;font-weight:bold;color:#f9e2af;margin-bottom:14px;">
                Synthèse — {mot_cle} <span style="font-size:11px;font-weight:normal;color:#a6adc8;">({len(articles)} articles)</span>
            </div>
            <div style="font-size:13px;color:#cdd6f4;">{html_r}</div>
        </div>"""
    return f"""
    <div style="margin-bottom:16px;">
        <button onclick="var el=document.getElementById('{tab_id}_table');var open=el.style.display!=='none';el.style.display=open?'none':'block';this.querySelector('.arrow').textContent=open?'▼':'▲';"
                style="cursor:pointer;font-size:14px;font-weight:bold;padding:10px 18px;background:#313244;color:#cdd6f4;border:none;border-radius:8px;width:100%;text-align:left;margin-bottom:4px;">
            <span style="color:#a6adc8;font-size:12px;">Recherche du {date_affichee}</span>
            {badge}
            <span class="arrow" style="float:right;">▲</span>
        </button>
        <div id="{tab_id}_table">
            <table border="1" style="border-collapse:collapse;width:100%;margin-top:6px;">
            <tr style="background-color:#313244;color:#cdd6f4;">
                <th style="padding:8px;width:50px;">Langue</th>
                <th style="padding:8px;">Titre &amp; Résumé</th>
                <th style="padding:8px;width:70px;">Lien</th>
            </tr>
            {lignes_tableau}
            </table>
        </div>
        {section_resume}
    </div>"""

def generer_contenu_html(historique, date):
    contenu = (f"<h2>Résultats par sujet</h2>"
               f"<p style='color:gray;font-size:13px;'>Derniere mise a jour : {date}</p><hr>")
    if not historique:
        return contenu + "<p style='color:gray;font-style:italic;'>Aucun resultat.</p>"
    idx = 0
    for mot_cle, sessions in historique.items():
        if mot_cle.startswith("__resume_global__") or not isinstance(sessions, list):
            continue
        if sessions and isinstance(sessions[0], dict) and "articles" in sessions[0]:
            contenu += f"<div style='margin-bottom:32px;'><div style='font-size:20px;font-weight:bold;color:#89b4fa;padding:12px 0;border-bottom:2px solid #45475a;margin-bottom:16px;'>{mot_cle.upper()}</div>"
            for si, session in enumerate(sessions):
                date_session = session.get("date", "N/A")
                articles     = sorted(session.get("articles", []), key=lambda x: x.get("score", 0), reverse=True)
                rg           = session.get("resume_global", "")
                tab_id       = f"tab_{idx}_{si}"
                if not articles:
                    continue
                badge = ("<span style='background:#a6e3a1;color:#1e1e2e;font-size:10px;padding:2px 8px;border-radius:10px;margin-left:8px;'>NOUVEAU</span>" if si == 0 else "")
                contenu += generer_bloc_mot_cle(mot_cle, articles, tab_id, rg, date_session, badge)
            contenu += "</div>"
        else:
            tries = sorted(sessions, key=lambda x: x.get("score", 0), reverse=True)
            contenu += generer_bloc_mot_cle(mot_cle, tries, f"tab_{idx}_0", "", "Historique", "")
        idx += 1
    return contenu

def generer_html_complet(contenu_body, date):
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<!-- ts:{ts} -->
<meta http-equiv="Cache-Control" content="no-cache,no-store,must-revalidate">
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="Expires" content="0">
<title>Veille Technologique IA</title>
<style>
body{{font-family:Arial,sans-serif;background:#1e1e2e;color:#cdd6f4;margin:0;padding:20px;}}
h2{{color:#89b4fa;}}
table{{border-collapse:collapse;width:100%;margin-top:6px;}}
th{{background:#313244;color:#cdd6f4;padding:10px;}}
td{{padding:8px;border:1px solid #45475a;vertical-align:top;}}
a{{color:#89b4fa;}}
ul{{margin:6px 0 0 0;padding-left:18px;}}
li{{margin:4px 0;font-size:13px;color:#a6adc8;line-height:1.6;}}
p{{color:gray;font-size:13px;}}
</style>
</head>
<body>
{contenu_body}
<p style="margin-top:30px;text-align:center;font-size:11px;color:#45475a;">Mis à jour le {date} — Veille technologique automatisée</p>
</body>
</html>"""


def generer_html_complet_theme(contenu_body: str, date: str, theme: dict) -> str:
    bg     = theme.get("bg",     "#1e1e2e")
    surf   = theme.get("surf",   "#181825")
    ov     = theme.get("ov",     "#313244")
    txt    = theme.get("txt",    "#cdd6f4")
    sub    = theme.get("sub",    "#a6adc8")
    brd    = theme.get("brd",    "#45475a")
    blue   = theme.get("blue",   "#89b4fa")
    font   = theme.get("font",   "Arial,sans-serif")
    fs     = theme.get("fs",     "13")
    rad    = theme.get("rad",    "8")
    yel    = theme.get("yel",    "#f9e2af")
    ptitle = theme.get("ptitle", "Veille Technologique IA")
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<!-- ts:{ts} -->
<meta http-equiv="Cache-Control" content="no-cache,no-store,must-revalidate">
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="Expires" content="0">
<title>{ptitle}</title>
<style>
body{{font-family:{font};background:{bg};color:{txt};margin:0;padding:20px;font-size:{fs}px;}}
h2{{color:{blue};}}
hr{{border-color:{brd};}}
table{{border-collapse:collapse;width:100%;margin-top:6px;}}
th{{background:{ov};color:{txt};padding:10px;text-align:left;}}
td{{padding:8px;border:1px solid {brd};vertical-align:top;}}
a{{color:{blue};}}
ul{{margin:6px 0 0 0;padding-left:18px;}}
li{{margin:4px 0;font-size:{fs}px;color:{sub};line-height:1.6;}}
p{{color:{sub};font-size:{fs}px;}}
button{{cursor:pointer;background:{ov};color:{txt};border:1px solid {brd};
        border-radius:{rad}px;padding:10px 18px;font-size:14px;font-weight:bold;width:100%;text-align:left;}}
</style>
</head>
<body>
{contenu_body}
<p style="margin-top:30px;text-align:center;font-size:11px;color:{brd};">Mis à jour le {date} — Veille technologique automatisée</p>
</body>
</html>"""

# ============================================================
# PUBLICATION WORDPRESS
# ============================================================

def publier_wordpress(contenu, page_id):
    base = _wp_base()
    if not base or not page_id:
        return False, "Config WordPress manquante"
    try:
        r = requests.post(
            f"{base}/pages/{page_id}",
            headers=_get_wp_headers(),
            json={"title": "Veille Technologique", "content": contenu, "status": "publish"},
            timeout=15
        )
        if r.status_code in [200, 201]:
            return True, "WordPress mis a jour"
        return False, f"Erreur WP {r.status_code}"
    except Exception as e:
        return False, f"Erreur WP : {e}"

# ============================================================
# PUBLICATION FTP
# ============================================================

def _uploader_ftp(html_final: str, chemin: str = None) -> tuple:
    ftp_cfg = _ftp_config()
    try:
        ftp = ftplib.FTP()
        ftp.connect(ftp_cfg["host"], 21, timeout=30)
        ftp.login(ftp_cfg["user"], ftp_cfg["password"])
        if not chemin:
            racine  = ftp.nlst()
            dossier = "/htdocs"
            if "htdocs" not in racine:
                for d in racine:
                    if any(x in d.lower() for x in ["htdocs", "www", "public"]):
                        dossier = f"/{d}"
                        break
            chemin = ftp_cfg["path"] if ftp_cfg["path"] else f"{dossier}/veille-ia.html"
        ftp.storbinary(f"STOR {chemin}", io.BytesIO(html_final.encode("utf-8")))
        ftp.quit()
        return True, f"FTP OK → {chemin}"
    except Exception as e:
        return False, f"Erreur FTP : {e}"


def publier_ftp(html_final: str) -> tuple:
    return _uploader_ftp(html_final)


def _publier_ftp_avec_historique(contenu_html_ignoré, historique_actuel: dict, theme: dict = None) -> tuple:
    """
    Publie l'historique Supabase/local sur FTP.
    theme optionnel : applique le thème personnalisé de l'utilisateur.
    """
    date_maj = datetime.now().strftime("%d/%m/%Y")
    contenu  = generer_contenu_html(historique_actuel, date_maj)
    if theme:
        html_final = generer_html_complet_theme(contenu, date_maj, theme)
    else:
        html_final = generer_html_complet(contenu, date_maj)
    ok, msg = _uploader_ftp(html_final)
    if ok:
        nb_sujets   = len([k for k in historique_actuel if not k.startswith("__")])
        nb_sessions = sum(len(v) for v in historique_actuel.values() if isinstance(v, list))
        msg = f"FTP OK — {nb_sujets} sujets, {nb_sessions} sessions"
    return ok, msg

# ============================================================
# CRÉATION DE POST WORDPRESS
# ============================================================

def creer_post_wordpress(contenu, sujet, date):
    base = _wp_base()
    if not base:
        return False, "Config WordPress manquante"
    try:
        r = requests.post(
            f"{base}/posts",
            headers=_get_wp_headers(),
            json={"title": f"{sujet} — {date}", "content": contenu, "status": "publish"},
            timeout=15
        )
        if r.status_code in [200, 201]:
            return True, "Post cree"
        return False, f"Erreur WP {r.status_code}"
    except Exception as e:
        return False, f"Erreur post : {e}"

def supprimer_anciens_posts():
    base = _wp_base()
    if not base:
        return 0
    try:
        r = requests.get(f"{base}/posts?per_page=100&status=publish,private,draft",
                         headers=_get_wp_headers(), timeout=15)
        posts = r.json() if r.status_code == 200 else []
        if not isinstance(posts, list):
            return 0
        supprimes = 0
        for post in posts:
            titre = post.get("title", {}).get("rendered", "").lower()
            if "veille ia" in titre or "veille :" in titre:
                requests.delete(f"{base}/posts/{post['id']}?force=true",
                                headers=_get_wp_headers(), timeout=10)
                supprimes += 1
        return supprimes
    except Exception:
        return 0

# ============================================================
# WORKFLOW COMPLET
# ============================================================

def workflow_publier(sujet, resultats_recherche, callback_statut=None,
                     limite=12, theme_ftp: dict = None):
    """
    theme_ftp : thème personnalisé optionnel pour la page FTP.
                Si None, utilise le thème Catppuccin par défaut.
                Passé par cron.py (depuis la config Supabase de l'utilisateur)
                et par app.py (depuis st.session_state["theme_ftp"]).
    """
    def statut(msg):
        if callback_statut:
            callback_statut(msg)

    sujet      = sujet.strip().lower()
    date       = datetime.now().strftime("%d/%m/%Y")
    historique = _charger_historique_ctx()
    sessions   = historique.get(sujet, [])
    tous_hrefs = {a["href"] for s in sessions for a in s.get("articles", []) if "href" in a}

    import time
    nb_max            = max(1, min(int(limite), 50))
    nouveaux_articles = []

    for r in resultats_recherche:
        href = r.get("href", "")
        if not href or href in tous_hrefs:
            continue
        if len(nouveaux_articles) >= nb_max:
            break
        statut(f"Resume IA {len(nouveaux_articles)+1}/{nb_max} : {r.get('title','')[:45]}...")
        resume = resumer_article_ollama(r.get("title", ""), href, r.get("body", ""))
        nouveaux_articles.append({
            "title":          r.get("title", ""),
            "href":           href,
            "score":          r.get("score", 0),
            "resume_ollama":  resume,
            "date_recherche": date,
        })
        time.sleep(4)

    if not nouveaux_articles:
        statut("Aucun nouvel article — historique inchange.")
        contenu      = generer_contenu_html(historique, date)
        html_complet = generer_html_complet(contenu, date)
    else:
        nouveaux_articles = detecter_doublons_contenu(nouveaux_articles, sessions)
        resume_precedent = ""
        for s in sessions:
            rg = s.get("resume_global", "")
            if rg and not rg.startswith("Erreur") and not rg.startswith("Aucun"):
                resume_precedent = rg
                break
        statut("Synthese globale...")
        time.sleep(10)
        resume_global = generer_resume_global(sujet, nouveaux_articles)
        if resume_precedent and not resume_global.startswith("Erreur"):
            if SequenceMatcher(None, normaliser(resume_global), normaliser(resume_precedent)).ratio() > 0.85:
                statut("Synthese similaire — conservee.")
                resume_global = resume_precedent
        session_du_jour = next((s for s in sessions if s.get("date") == date), None)
        if session_du_jour:
            session_du_jour["articles"].extend(nouveaux_articles)
            session_du_jour["resume_global"] = resume_global
        else:
            sessions.insert(0, {"date": date, "articles": nouveaux_articles, "resume_global": resume_global})
        historique[sujet] = sessions
        # ── Sauvegarde dans Supabase (ou local si pas de storage) ──
        _sauvegarder_historique_ctx(historique)
        statut("Generation HTML...")
        contenu      = generer_contenu_html(historique, date)
        html_complet = generer_html_complet(contenu, date)

    resultats = {}
    page_id   = obtenir_ou_creer_page()
    statut("Publication WordPress...")
    ok, msg = publier_wordpress(contenu, page_id)
    resultats["wordpress"] = (ok, msg)

    if ftp_est_configure():
        statut("Upload FTP...")
        # Passe le thème utilisateur si disponible
        ok2, msg2 = _publier_ftp_avec_historique(html_complet, historique, theme_ftp)
        resultats["ftp"] = (ok2, msg2)
    else:
        resultats["ftp"] = (True, "FTP non configure — ignore")

    statut("Publication terminee !")
    return resultats


def workflow_creer_post(sujet, resultats_recherche, callback_statut=None):
    def statut(msg):
        if callback_statut:
            callback_statut(msg)

    date                 = datetime.now().strftime("%d/%m/%Y")
    nb                   = len(resultats_recherche)
    lignes               = ""
    articles_pour_global = []

    for i, r in enumerate(resultats_recherche):
        statut(f"Resume IA {i+1}/{nb}...")
        resume = resumer_article_ollama(r.get("title", ""), r.get("href", ""), r.get("body", ""))
        dom    = urlparse(r.get("href", "")).netloc
        langue = "FR" if dom.endswith(".fr") or any(d in dom for d in DOMAINES_FR_PRIORITAIRES) else "EN"
        html_pts = "<ul style='margin:6px 0 0 0;padding-left:18px;'>"
        for pt in resume:
            html_pts += f"<li style='margin:4px 0;font-size:12px;color:#6c7086;'>{pt}</li>"
        html_pts += "</ul>"
        lignes += f"""
        <tr>
            <td style="padding:8px;text-align:center;">{langue}</td>
            <td style="padding:8px;"><strong>{r.get('title','')}</strong>{html_pts}</td>
            <td style="padding:8px;text-align:center;"><a href="{r.get('href','#')}" target="_blank">ouvrir</a></td>
        </tr>"""
        articles_pour_global.append({**r, "resume_ollama": resume})

    statut("Synthese globale...")
    rg      = generer_resume_global(sujet, articles_pour_global)
    rg_html = _formater_resume_html(rg, articles_pour_global)
    contenu = f"""
    <h2>{sujet}</h2>
    <p style="color:gray;">Publié le {date}</p>
    <table border="1" style="border-collapse:collapse;width:100%;">
    <tr style="background:#313244;color:#cdd6f4;"><th>Langue</th><th>Titre &amp; Résumé</th><th>Lien</th></tr>
    {lignes}</table>
    <div style="margin-top:24px;padding:18px;background:#f8f9fa;border-left:4px solid #f9e2af;border-radius:8px;">
        <strong>Synthèse — {sujet}</strong>
        <div style="margin-top:12px;font-size:13px;">{rg_html}</div>
    </div>"""
    statut("Creation du post WordPress...")
    ok, msg = creer_post_wordpress(contenu, sujet, date)
    statut("Post cree !" if ok else f"Erreur : {msg}")
    return ok, msg