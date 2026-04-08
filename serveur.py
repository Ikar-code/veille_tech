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
    import settings
    _TIMEOUT_COURT    = getattr(settings, "TIMEOUT_HTTP_COURT",    8)
    _TIMEOUT_STANDARD = getattr(settings, "TIMEOUT_HTTP_STANDARD", 15)
    _TIMEOUT_LONG     = getattr(settings, "TIMEOUT_HTTP_LONG",     30)
    _SCORE_MIN_PRI    = getattr(settings, "SCORE_MIN_PRIMAIRE",    50)
    _SCORE_MIN_SEC    = getattr(settings, "SCORE_MIN_SECONDAIRE",  35)
    _MAX_ARTICLES     = getattr(settings, "MAX_ARTICLES_PAR_RECHERCHE", 50)
    _DELAI_RESUME     = getattr(settings, "DELAI_RESUME_SECONDES",  4)
    _DELAI_SYNTHESE   = getattr(settings, "DELAI_SYNTHESE_SECONDES",10)
except ImportError:
    _TIMEOUT_COURT    = 8
    _TIMEOUT_STANDARD = 15
    _TIMEOUT_LONG     = 30
    _SCORE_MIN_PRI    = 50
    _SCORE_MIN_SEC    = 35
    _MAX_ARTICLES     = 50
    _DELAI_RESUME     = 4
    _DELAI_SYNTHESE   = 10

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

# ============================================================
# MARQUEURS JSON EMBARQUÉ (import/export HTML)
# ============================================================
_FTP_DATA_MARKER = "<!--VEILLE_DATA:"
_FTP_DATA_END    = ":END_VEILLE_DATA-->"

def _format_embedded_historique(historique: dict) -> str:
    if not historique:
        return ""
    try:
        return f"\n{_FTP_DATA_MARKER}{json.dumps(historique, ensure_ascii=False)}{_FTP_DATA_END}\n"
    except Exception:
        return ""

def extraire_historique_depuis_html(html: str) -> dict:
    """Extrait le JSON embarqué d'un fichier HTML généré par cette app."""
    try:
        debut = html.find(_FTP_DATA_MARKER)
        fin   = html.find(_FTP_DATA_END)
        if debut != -1 and fin != -1:
            json_str = html[debut + len(_FTP_DATA_MARKER):fin]
            return json.loads(json_str)
    except Exception:
        pass
    return {}

# ============================================================
# CONTEXTE STORAGE
# ============================================================
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

# ============================================================
# CONSTANTES
# ============================================================
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

def est_domaine_bloque(domain: str) -> bool:
    domain = domain.lower()
    if domain.endswith(".gouv.fr"):
        return True
    if any(d in domain for d in DOMAINES_GOUVERNEMENTAUX_BLOQUES):
        return True
    return False

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
                         headers={"Authorization": f"Basic {token}"},
                         timeout=_TIMEOUT_COURT)
        if r.status_code == 200:
            return True, f"Connexion reussie ! Connecte : {r.json().get('name', user)}"
        elif r.status_code == 401: return False, "Identifiants incorrects."
        elif r.status_code == 403: return False, "Acces refuse."
        elif r.status_code == 404: return False, "URL introuvable."
        else: return False, f"Erreur {r.status_code}."
    except requests.exceptions.ConnectionError:
        est_local = any(x in url.lower() for x in ["localhost",".local","127.0.0.1"])
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
        ftp.connect(host, 21, timeout=_TIMEOUT_COURT)
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
        "host":     config.get("ftp_host",     ""),
        "user":     config.get("ftp_user",     ""),
        "password": config.get("ftp_password", ""),
        "path":     config.get("ftp_path",     "/htdocs/veille-ia.html"),
    }

def ftp_est_configure():
    cfg = _ftp_config()
    placeholders = {"","if0_xxxxxxx","xxxx xxxx xxxx","votre mot de passe ftp"}
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
            if "veille ia" in page.get("title",{}).get("rendered","").lower():
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
    if est_domaine_bloque(dom):
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
                resumes_existants.append((" ".join(pts).lower(), a.get("title",""), a.get("href","")))
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
            }, timeout=_TIMEOUT_LONG
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
        inacc  = not points or points in [["Contenu non accessible pour ce site."],["Résumé non disponible."]]
        if not inacc:
            contexte += f"\n[{i+1}] {titre} ({dom})\n"
            for p in points[:3]:
                contexte += f"  - {p}\n"
        else:
            body = a.get("body","").strip()
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
            }, timeout=_TIMEOUT_LONG
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
                json={"model":"llama-3.3-70b-versatile","max_tokens":3000,
                      "messages":[{"role":"user","content":contexte[:2000]}]},
                timeout=_TIMEOUT_LONG
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
    date_new       = session_nouvelle.get("date","récente")
    date_old       = session_ancienne.get("date","précédente")
    hrefs_anciens  = {a["href"] for a in session_ancienne.get("articles",[]) if "href" in a}
    nouveaux       = [a for a in session_nouvelle.get("articles",[]) if a.get("href") and a["href"] not in hrefs_anciens]
    hrefs_nouveaux = {a["href"] for a in session_nouvelle.get("articles",[]) if "href" in a}
    disparus       = [a for a in session_ancienne.get("articles",[]) if a.get("href") and a["href"] not in hrefs_nouveaux]
    if not nouveaux and not disparus:
        return f"Aucune différence entre les sessions du {date_old} et du {date_new}."
    contexte = (f"Session précédente : {date_old} ({len(session_ancienne.get('articles') or [])} articles)\n"
                f"Session récente : {date_new} ({len(session_nouvelle.get('articles') or [])} articles)\n\n")
    if nouveaux:
        contexte += f"NOUVEAUX ARTICLES ({len(nouveaux)}) :\n"
        for a in nouveaux[:6]:
            pts = a.get("resume_ollama",[])
            contexte += f"- {a.get('title','')}\n"
            if pts and pts != ["Contenu non accessible pour ce site."]:
                for p in pts[:2]:
                    contexte += f"  · {p}\n"
    if disparus:
        contexte += f"\nARTICLES DISPARUS ({len(disparus)}) :\n"
        for a in disparus[:4]:
            contexte += f"- {a.get('title','')}\n"
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
                    {"role":"system","content":"Tu compares deux sessions de veille technologique."},
                    {"role":"user","content":f"Sujet : \"{sujet}\"\n\n{contexte}\n\nRédige un résumé des évolutions."}
                ]
            }, timeout=_TIMEOUT_LONG
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
                        lien = r.get("href","#")
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
                    lien  = entry.get("link","")
                    titre = entry.get("title","")
                    body  = entry.get("summary","")
                    if not lien or lien in ids_vus:
                        continue
                    if any(m in normaliser(titre) or m in normaliser(body) for m in mots):
                        ids_vus.add(lien)
                        data.append({"title":titre,"body":body,"href":lien,"source":"rss"})
            except Exception:
                continue

    statut("Filtrage et scoring...")
    data = [r for r in data if not est_bloque(r, sujet_brut)]
    data = [scorer_resultat(r, sujet_brut) for r in data]
    data.sort(key=lambda x: x["score"], reverse=True)
    data = deduplique_semantique(data)
    filtres = [r for r in data if r["score"] >= _SCORE_MIN_PRI]
    if not filtres:
        filtres = [r for r in data if r["score"] >= _SCORE_MIN_SEC]
    filtres = filtres[:_MAX_ARTICLES]
    statut(f"{len(filtres)} resultats trouves")
    return filtres

# ============================================================
# GÉNÉRATION HTML — CSS + JS partagés
# ============================================================

_CSS_VUES = """
*{box-sizing:border-box}
body{margin:0;padding:0}
#vue-selector{
    display:flex;align-items:center;
    padding:12px 20px;background:var(--surf);
    border-bottom:1px solid var(--brd);
    position:sticky;top:0;z-index:100;
}
.vue-btn{
    background:transparent;color:var(--sub);
    border:1px solid var(--brd);border-radius:6px;
    padding:6px 14px;font-size:12px;cursor:pointer;margin-right:6px;
    transition:all .15s;
}
.vue-btn:hover,.vue-btn.active{background:var(--blue);color:var(--bg);border-color:var(--blue)}
.maj-date{color:var(--sub);font-size:12px;margin:10px 20px 0}
hr{border:none;border-top:1px solid var(--brd);margin:6px 20px 16px}
/* ── Onglets ── */
.onglets-nav{
    display:flex;flex-wrap:wrap;gap:6px;
    padding:12px 20px;background:var(--surf);
    border-bottom:1px solid var(--brd);
    position:sticky;top:49px;z-index:99;
}
.onglet-btn{
    background:transparent;color:var(--sub);
    border:1px solid var(--brd);border-radius:20px;
    padding:6px 16px;font-size:13px;cursor:pointer;transition:all .15s;
}
.onglet-btn:hover,.onglet-btn.active{background:var(--blue);color:var(--bg);border-color:var(--blue)}
.onglets-body{padding:20px}
/* ── Accordéon ── */
.acc-item{border-bottom:1px solid var(--brd)}
.acc-header{
    width:100%;display:flex;align-items:center;gap:12px;
    background:var(--surf);color:var(--txt);
    border:none;padding:14px 20px;cursor:pointer;text-align:left;transition:background .15s;
}
.acc-header:hover{background:var(--ov)}
.acc-title{font-weight:700;font-size:15px;flex:1}
.acc-count{font-size:12px;color:var(--sub);background:var(--ov);padding:2px 10px;border-radius:12px}
.acc-arrow{font-size:12px;color:var(--sub);margin-left:auto}
.acc-body{padding:20px}
/* ── Sidebar ── */
#vue-sidebar-wrap{display:flex!important}
.sb-nav{
    width:220px;flex-shrink:0;
    border-right:1px solid var(--brd);background:var(--surf);
    padding:12px 0;min-height:calc(100vh - 120px);
}
.sb-item{
    width:100%;display:flex;justify-content:space-between;align-items:center;
    background:transparent;color:var(--sub);border:none;
    padding:10px 16px;cursor:pointer;text-align:left;font-size:13px;
    transition:all .15s;border-left:3px solid transparent;
}
.sb-item:hover{background:var(--ov);color:var(--txt)}
.sb-item.active{background:var(--ov);color:var(--blue);border-left-color:var(--blue)}
.sb-title{flex:1}
.sb-badge{
    font-size:11px;background:var(--ov);color:var(--sub);
    padding:1px 8px;border-radius:10px;min-width:28px;text-align:center;
}
.sb-item.active .sb-badge{background:var(--blue);color:var(--bg)}
.sb-main{flex:1;padding:20px;overflow-x:auto}
.sb-content{display:none}
/* ── Sessions ── */
.session-block{margin-bottom:12px;border:1px solid var(--brd);border-radius:10px;overflow:hidden}
.session-header{
    width:100%;display:flex;align-items:center;gap:10px;
    background:var(--ov);color:var(--txt);
    border:none;padding:10px 16px;cursor:pointer;text-align:left;
}
.session-header:hover{filter:brightness(1.1)}
.session-date{font-weight:600;font-size:13px}
.session-meta{font-size:12px;color:var(--sub);flex:1}
.sess-arrow{font-size:11px;color:var(--sub)}
.badge-new{
    background:#a6e3a1;color:#1e1e2e;
    font-size:10px;padding:1px 7px;border-radius:8px;font-weight:700;
}
/* ── Synthèse ── */
.synth-box{
    margin:14px 14px 10px;padding:14px 16px;
    background:linear-gradient(135deg,var(--bg),var(--surf));
    border-left:4px solid var(--yel);border-radius:8px;
}
.synth-title{font-size:13px;font-weight:700;color:var(--yel);margin-bottom:10px}
.synth-body{font-size:13px;color:var(--txt)}
/* ── Grille articles ── */
.articles-grid{
    display:grid;
    grid-template-columns:repeat(auto-fill,minmax(320px,1fr));
    gap:10px;padding:14px;
}
.art-card{
    background:var(--surf);border:1px solid var(--brd);
    border-radius:8px;padding:12px 14px;transition:border-color .15s;
}
.art-card:hover{border-color:var(--blue)}
.art-header{margin-bottom:6px}
.art-title{
    color:var(--blue);font-size:13px;font-weight:600;
    text-decoration:none;line-height:1.4;display:block;
}
.art-title:hover{text-decoration:underline}
.art-meta{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px}
.art-dom{font-size:11px;color:var(--sub)}
.art-score{font-size:11px;padding:1px 8px;border-radius:10px;font-weight:700}
.score-hi{background:rgba(166,227,161,.2);color:#a6e3a1}
.score-mid{background:rgba(249,226,175,.2);color:#f9e2af}
.score-lo{background:rgba(243,139,168,.2);color:#f38ba8}
.art-pts{margin:0;padding-left:16px;font-size:12px;color:var(--sub);line-height:1.6}
.art-pts li{margin:2px 0}
.badge-doublon{
    font-size:10px;background:rgba(249,226,175,.2);color:#f9e2af;
    border:1px solid #f9e2af;padding:1px 6px;border-radius:6px;margin-left:6px;
}
"""

_JS_VUES = """
function setVue(vue){
    ['onglets','accordeon','sidebar'].forEach(function(v){
        var wrap = v==='sidebar'?'sidebar-wrap':v;
        var el=document.getElementById('vue-'+wrap);
        if(el) el.style.display=(v===vue)?(v==='sidebar'?'flex':'block'):'none';
        var btn=document.getElementById('vue-btn-'+v);
        if(btn) btn.classList.toggle('active',v===vue);
    });
    try{localStorage.setItem('veille_vue',vue);}catch(e){}
}
function showTab(id){
    document.querySelectorAll('.tab-content').forEach(function(el){el.style.display='none';});
    document.querySelectorAll('.onglet-btn').forEach(function(el){el.classList.remove('active');});
    var t=document.getElementById('tab-'+id);
    if(t) t.style.display='block';
    document.querySelectorAll('.onglet-btn').forEach(function(btn){
        if(btn.getAttribute('onclick')&&btn.getAttribute('onclick').indexOf(id)!==-1)
            btn.classList.add('active');
    });
}
function toggleAcc(id){
    var b=document.getElementById('acc-'+id);
    var a=document.getElementById('acc-arrow-'+id);
    if(!b) return;
    var open=b.style.display!=='none';
    b.style.display=open?'none':'block';
    if(a) a.textContent=open?'▼':'▲';
}
function showSidebar(id){
    document.querySelectorAll('.sb-content').forEach(function(el){el.style.display='none';});
    document.querySelectorAll('.sb-item').forEach(function(el){el.classList.remove('active');});
    var c=document.getElementById('sb-'+id);
    if(c) c.style.display='block';
    document.querySelectorAll('.sb-item').forEach(function(btn){
        if(btn.getAttribute('onclick')&&btn.getAttribute('onclick').indexOf(id)!==-1)
            btn.classList.add('active');
    });
}
function toggleSession(id){
    var el=document.getElementById(id);
    var ar=document.getElementById('arr-'+id);
    if(!el) return;
    var open=el.style.display!=='none';
    el.style.display=open?'none':'block';
    if(ar) ar.textContent=open?'▼':'▲';
}
document.addEventListener('DOMContentLoaded',function(){
    try{var s=localStorage.getItem('veille_vue');if(s) setVue(s);}catch(e){}
});
"""


def _safe_id(texte: str) -> str:
    return re.sub(r'[^a-z0-9]', '-', texte.lower().strip())[:40]


def _compter_articles(sessions: list) -> int:
    return sum(len(s.get("articles",[])) for s in sessions if isinstance(s, dict))


def _formater_resume_html(texte, articles_ref):
    if not texte:
        return ""
    index_urls = {i+1: (a.get("href",""), urlparse(a.get("href","")).netloc)
                  for i, a in enumerate(articles_ref[:12])}

    def remplacer_citation(m):
        num = int(m.group(1))
        if num in index_urls:
            url_r, dom_r = index_urls[num]
            return (f' <a href="{url_r}" target="_blank" '
                    f'style="color:var(--blue);font-size:11px;text-decoration:none;" '
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
            html += f"<div style='font-size:13px;font-weight:bold;color:var(--yel);margin:14px 0 6px 0;'>— {titre}</div>"
        elif ligne.startswith("##"):
            titre = ligne.lstrip("# ").rstrip(": ").strip()
            html += f"<div style='font-size:13px;font-weight:bold;color:var(--yel);margin:14px 0 6px 0;'>— {titre}</div>"
        elif ligne.startswith(("- ","* ","• ")):
            point = re.sub(r'\*\*', '', ligne.lstrip("-*• ").strip())
            point = point.replace("<","&lt;").replace(">","&gt;")
            point = re.sub(r'\[(\d+)\]', remplacer_citation, point)
            html += f"<div style='padding:3px 0 3px 14px;border-left:2px solid var(--brd);margin:3px 0;line-height:1.6;'>{point}</div>"
        else:
            ligne = re.sub(r'\*\*', '', ligne).replace("<","&lt;").replace(">","&gt;")
            ligne = re.sub(r'\[(\d+)\]', remplacer_citation, ligne)
            html += f"<p style='margin:6px 0;line-height:1.7;'>{ligne}</p>"
    return html


def _generer_bloc_sujet(sujet: str, sessions: list) -> str:
    html = ""
    for i, session in enumerate(sessions):
        if not isinstance(session, dict):
            continue
        date_s   = session.get("date","N/A")
        articles = sorted(session.get("articles",[]),
                          key=lambda x: x.get("score",0), reverse=True)
        rg       = session.get("resume_global","")
        if not articles:
            continue

        is_open = (i == 0)
        display = "block" if is_open else "none"
        arrow   = "▲" if is_open else "▼"
        badge   = "<span class='badge-new'>NOUVEAU</span>" if i == 0 else ""
        sid     = f"sess-{_safe_id(sujet)}-{i}"

        html += f"""
        <div class="session-block">
            <button class="session-header" onclick="toggleSession('{sid}')">
                <span class="session-date">📅 {date_s}</span>
                <span class="session-meta">{len(articles)} articles {badge}</span>
                <span id="arr-{sid}" class="sess-arrow">{arrow}</span>
            </button>
            <div id="{sid}" style="display:{display}">"""

        if rg and not rg.startswith("Erreur"):
            html_rg = _formater_resume_html(rg, articles)
            html += f"""
                <div class="synth-box">
                    <div class="synth-title">Synthèse — {date_s}</div>
                    <div class="synth-body">{html_rg}</div>
                </div>"""

        html += '<div class="articles-grid">'
        for a in articles:
            dom    = urlparse(a.get("href","")).netloc
            score  = a.get("score",0)
            pts    = a.get("resume_ollama",[])
            doublon = a.get("doublon_de","")
            score_cls = "score-hi" if score>=80 else "score-mid" if score>=50 else "score-lo"
            pts_html = ""
            if pts and pts not in [["Contenu non accessible pour ce site."],["Résumé non disponible."]]:
                items = "".join(f"<li>{p}</li>" for p in pts[:3])
                pts_html = f"<ul class='art-pts'>{items}</ul>"
            doublon_html = "<span class='badge-doublon'>~ doublon</span>" if doublon else ""
            html += f"""
                <div class="art-card">
                    <div class="art-header">
                        <a href="{a.get('href','#')}" target="_blank" class="art-title">{a.get('title','')}</a>
                        {doublon_html}
                    </div>
                    <div class="art-meta">
                        <span class="art-dom">{dom}</span>
                        <span class="art-score {score_cls}">{score}</span>
                    </div>
                    {pts_html}
                </div>"""
        html += "</div></div></div>"
    return html


def generer_contenu_html(historique, date):
    """Génère le contenu HTML avec navigation onglets/accordéon/sidebar."""
    if not historique:
        return "<p style='color:var(--sub);font-style:italic;'>Aucun résultat.</p>"

    sujets = [k for k, v in historique.items()
              if not k.startswith("__") and isinstance(v, list) and v]
    if not sujets:
        return "<p style='color:var(--sub);font-style:italic;'>Aucun résultat.</p>"

    blocs = {s: _generer_bloc_sujet(s, historique[s]) for s in sujets}

    # ── Onglets ──────────────────────────────────────────────
    onglets_nav = ""
    for i, s in enumerate(blocs):
        onglets_nav += (
            f'<button class="onglet-btn{" active" if i==0 else ""}" '
            f'onclick="showTab(\'{_safe_id(s)}\')">{s.title()}</button>'
        )
    onglets_content = ""
    for i, (s, bloc) in enumerate(blocs.items()):
        onglets_content += (
            f'<div id="tab-{_safe_id(s)}" class="tab-content" '
            f'style="display:{"block" if i==0 else "none"}">{bloc}</div>'
        )

    # ── Accordéon ────────────────────────────────────────────
    accordeon = ""
    for i, (s, bloc) in enumerate(blocs.items()):
        expanded = "block" if i == 0 else "none"
        arrow    = "▲" if i == 0 else "▼"
        nb       = _compter_articles(historique[s])
        accordeon += f"""
        <div class="acc-item">
            <button class="acc-header" onclick="toggleAcc('{_safe_id(s)}')">
                <span class="acc-title">{s.title()}</span>
                <span class="acc-count">{nb} articles</span>
                <span id="acc-arrow-{_safe_id(s)}" class="acc-arrow">{arrow}</span>
            </button>
            <div id="acc-{_safe_id(s)}" class="acc-body" style="display:{expanded}">{bloc}</div>
        </div>"""

    # ── Sidebar ───────────────────────────────────────────────
    sb_nav = ""
    for i, s in enumerate(blocs):
        nb = _compter_articles(historique[s])
        sb_nav += (
            f'<button class="sb-item{" active" if i==0 else ""}" '
            f'onclick="showSidebar(\'{_safe_id(s)}\')">'
            f'<span class="sb-title">{s.title()}</span>'
            f'<span class="sb-badge">{nb}</span></button>'
        )
    sb_content = ""
    for i, (s, bloc) in enumerate(blocs.items()):
        sb_content += (
            f'<div id="sb-{_safe_id(s)}" class="sb-content" '
            f'style="display:{"block" if i==0 else "none"}">{bloc}</div>'
        )

    return f"""
    <div id="vue-selector">
        <span style="font-size:13px;opacity:.7;margin-right:10px;">Affichage :</span>
        <button class="vue-btn active" onclick="setVue('onglets')" id="vue-btn-onglets">⊞ Onglets</button>
        <button class="vue-btn" onclick="setVue('accordeon')" id="vue-btn-accordeon">☰ Accordéon</button>
        <button class="vue-btn" onclick="setVue('sidebar')" id="vue-btn-sidebar">◧ Sidebar</button>
    </div>
    <p class="maj-date">Dernière mise à jour : {date}</p>
    <hr>

    <div id="vue-onglets" class="vue-container">
        <div class="onglets-nav">{onglets_nav}</div>
        <div class="onglets-body">{onglets_content}</div>
    </div>

    <div id="vue-accordeon" class="vue-container" style="display:none">{accordeon}</div>

    <div id="vue-sidebar-wrap" class="vue-container" style="display:none">
        <div class="sb-nav">{sb_nav}</div>
        <div class="sb-main">{sb_content}</div>
    </div>
    """


def _build_html_head(title: str, theme_vars: str, font: str, fs: str) -> str:
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
<title>{title}</title>
<style>
:root{{{theme_vars}}}
body{{font-family:{font};background:var(--bg);color:var(--txt);margin:0;padding:0;font-size:{fs}px;}}
{_CSS_VUES}
</style>
</head>
<body>"""


def generer_html_complet(contenu_body, date, historique_embed=None):
    theme_vars = (
        "--bg:#1e1e2e;--surf:#181825;--ov:#313244;"
        "--txt:#cdd6f4;--sub:#a6adc8;--brd:#45475a;"
        "--blue:#89b4fa;--grn:#a6e3a1;--yel:#f9e2af;--red:#f38ba8;"
    )
    embed = _format_embedded_historique(historique_embed) if historique_embed else ""
    head  = _build_html_head("Veille Technologique IA", theme_vars, "Arial,sans-serif", "13")
    return f"""{head}
<div style="padding:16px 20px 4px;background:var(--surf);border-bottom:1px solid var(--brd);">
    <h1 style="margin:0;font-size:20px;color:var(--blue);">🔭 Veille Technologique IA</h1>
</div>
{contenu_body}
<p style="text-align:center;font-size:11px;color:var(--brd);padding:20px;">
    Mis à jour le {date} — Veille technologique automatisée
</p>
<script>{_JS_VUES}</script>
{embed}
</body></html>"""


def generer_html_complet_theme(contenu_body: str, date: str, theme: dict, historique_embed=None) -> str:
    bg     = theme.get("bg",     "#1e1e2e")
    surf   = theme.get("surf",   "#181825")
    ov     = theme.get("ov",     "#313244")
    txt    = theme.get("txt",    "#cdd6f4")
    sub    = theme.get("sub",    "#a6adc8")
    brd    = theme.get("brd",    "#45475a")
    blue   = theme.get("blue",   "#89b4fa")
    grn    = theme.get("grn",    "#a6e3a1")
    yel    = theme.get("yel",    "#f9e2af")
    red    = theme.get("red",    "#f38ba8")
    font   = theme.get("font",   "Arial,sans-serif")
    fs     = theme.get("fs",     "13")
    ptitle = theme.get("ptitle", "Veille Technologique IA")

    theme_vars = (
        f"--bg:{bg};--surf:{surf};--ov:{ov};"
        f"--txt:{txt};--sub:{sub};--brd:{brd};"
        f"--blue:{blue};--grn:{grn};--yel:{yel};--red:{red};"
    )
    embed = _format_embedded_historique(historique_embed) if historique_embed else ""
    head  = _build_html_head(ptitle, theme_vars, font, fs)
    return f"""{head}
<div style="padding:16px 20px 4px;background:var(--surf);border-bottom:1px solid var(--brd);">
    <h1 style="margin:0;font-size:20px;color:var(--blue);">🔭 {ptitle}</h1>
</div>
{contenu_body}
<p style="text-align:center;font-size:11px;color:var(--brd);padding:20px;">
    Mis à jour le {date} — Veille technologique automatisée
</p>
<script>{_JS_VUES}</script>
{embed}
</body></html>"""

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
            json={"title":"Veille Technologique","content":contenu,"status":"publish"},
            timeout=_TIMEOUT_STANDARD
        )
        if r.status_code in [200,201]:
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
        ftp.connect(ftp_cfg["host"], 21, timeout=_TIMEOUT_LONG)
        ftp.login(ftp_cfg["user"], ftp_cfg["password"])
        if not chemin:
            racine  = ftp.nlst()
            dossier = "/htdocs"
            if "htdocs" not in racine:
                for d in racine:
                    if any(x in d.lower() for x in ["htdocs","www","public"]):
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

def _publier_ftp_avec_historique(_, historique_actuel: dict, theme: dict = None) -> tuple:
    date_maj = datetime.now().strftime("%d/%m/%Y")
    contenu  = generer_contenu_html(historique_actuel, date_maj)
    if theme:
        html_final = generer_html_complet_theme(contenu, date_maj, theme, historique_actuel)
    else:
        html_final = generer_html_complet(contenu, date_maj, historique_actuel)
    ok, msg = _uploader_ftp(html_final)
    if ok:
        nb_s = len([k for k in historique_actuel if not k.startswith("__")])
        nb_r = sum(len(v) for v in historique_actuel.values() if isinstance(v, list))
        msg  = f"FTP OK — {nb_s} sujets, {nb_r} sessions"
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
            json={"title":f"{sujet} — {date}","content":contenu,"status":"publish"},
            timeout=_TIMEOUT_STANDARD
        )
        if r.status_code in [200,201]:
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
                         headers=_get_wp_headers(), timeout=_TIMEOUT_STANDARD)
        posts = r.json() if r.status_code == 200 else []
        if not isinstance(posts, list):
            return 0
        supprimes = 0
        for post in posts:
            titre = post.get("title",{}).get("rendered","").lower()
            if "veille ia" in titre or "veille :" in titre:
                requests.delete(f"{base}/posts/{post['id']}?force=true",
                                headers=_get_wp_headers(), timeout=_TIMEOUT_COURT)
                supprimes += 1
        return supprimes
    except Exception:
        return 0

# ============================================================
# WORKFLOW COMPLET
# ============================================================

def workflow_publier(sujet, resultats_recherche, callback_statut=None,
                     limite=12, theme_ftp: dict = None,
                     publier_wp: bool = True, publier_ftp: bool = True):
    def statut(msg):
        if callback_statut:
            callback_statut(msg)

    sujet      = sujet.strip().lower()
    date       = datetime.now().strftime("%d/%m/%Y")
    historique = _charger_historique_ctx()
    sessions   = historique.get(sujet, [])
    tous_hrefs = {a["href"] for s in sessions for a in s.get("articles",[]) if "href" in a}

    import time
    nb_max            = max(1, min(int(limite), _MAX_ARTICLES))
    nouveaux_articles = []

    for r in resultats_recherche:
        href = r.get("href","")
        if not href or href in tous_hrefs:
            continue
        if len(nouveaux_articles) >= nb_max:
            break
        statut(f"Résumé IA {len(nouveaux_articles)+1}/{nb_max} : {r.get('title','')[:45]}...")
        resume = resumer_article_ollama(r.get("title",""), href, r.get("body",""))
        nouveaux_articles.append({
            "title":          r.get("title",""),
            "href":           href,
            "score":          r.get("score",0),
            "resume_ollama":  resume,
            "date_recherche": date,
        })
        time.sleep(_DELAI_RESUME)

    if not nouveaux_articles:
        statut("Aucun nouvel article — historique inchangé.")
        contenu      = generer_contenu_html(historique, date)
        html_complet = generer_html_complet(contenu, date, historique)
    else:
        nouveaux_articles = detecter_doublons_contenu(nouveaux_articles, sessions)
        resume_precedent  = next(
            (s.get("resume_global","") for s in sessions
             if s.get("resume_global") and not s["resume_global"].startswith(("Erreur","Aucun"))),
            ""
        )
        statut("Synthèse globale…")
        time.sleep(_DELAI_SYNTHESE)
        resume_global = generer_resume_global(sujet, nouveaux_articles)
        if resume_precedent and not resume_global.startswith("Erreur"):
            if SequenceMatcher(None, normaliser(resume_global), normaliser(resume_precedent)).ratio() > 0.85:
                statut("Synthèse similaire — conservée.")
                resume_global = resume_precedent
        session_du_jour = next((s for s in sessions if s.get("date") == date), None)
        if session_du_jour:
            session_du_jour["articles"].extend(nouveaux_articles)
            session_du_jour["resume_global"] = resume_global
        else:
            sessions.insert(0, {"date":date,"articles":nouveaux_articles,"resume_global":resume_global})
        historique[sujet] = sessions
        _sauvegarder_historique_ctx(historique)
        statut("Génération HTML…")
        contenu      = generer_contenu_html(historique, date)
        html_complet = generer_html_complet(contenu, date, historique)

    resultats_pub = {}

    if publier_wp:
        page_id = obtenir_ou_creer_page()
        statut("Publication WordPress…")
        ok, msg = publier_wordpress(contenu, page_id)
        resultats_pub["wordpress"] = (ok, msg)
    else:
        resultats_pub["wordpress"] = (True, "WordPress ignoré")

    if publier_ftp:
        if ftp_est_configure():
            statut("Upload FTP…")
            ok2, msg2 = _publier_ftp_avec_historique(html_complet, historique, theme_ftp)
            resultats_pub["ftp"] = (ok2, msg2)
        else:
            resultats_pub["ftp"] = (False, "FTP non configuré — allez dans ⚙️ Configuration")
    else:
        resultats_pub["ftp"] = (True, "FTP ignoré")

    statut("Publication terminée !")
    return resultats_pub


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
        resume = resumer_article_ollama(r.get("title",""), r.get("href",""), r.get("body",""))
        dom    = urlparse(r.get("href","")).netloc
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
    <h2 style="color:var(--blue)">{sujet}</h2>
    <p style="color:var(--sub);">Publié le {date}</p>
    <table border="1" style="border-collapse:collapse;width:100%;">
    <tr style="background:var(--ov);color:var(--txt);"><th>Langue</th><th>Titre &amp; Résumé</th><th>Lien</th></tr>
    {lignes}</table>
    <div style="margin-top:24px;padding:18px;border-left:4px solid var(--yel);border-radius:8px;background:var(--surf);">
        <strong>Synthèse — {sujet}</strong>
        <div style="margin-top:12px;font-size:13px;">{rg_html}</div>
    </div>"""
    statut("Creation du post WordPress...")
    ok, msg = creer_post_wordpress(contenu, sujet, date)
    statut("Post cree !" if ok else f"Erreur : {msg}")
    return ok, msg
