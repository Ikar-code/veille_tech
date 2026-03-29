# ============================================================
# STORAGE.PY — Persistance Supabase (remplace les fichiers JSON)
# Utilisé par serveur.py pour config + historique
# ============================================================

import os
import json

# ── Connexion Supabase ─────────────────────────────────────
try:
    from supabase import create_client
    _url  = os.environ.get("SUPABASE_URL", "")
    _key  = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if _url and _key:
        _db = create_client(_url, _key)
        SUPABASE_OK = True
    else:
        _db = None
        SUPABASE_OK = False
except Exception:
    _db = None
    SUPABASE_OK = False

# ID utilisateur courant (injecté par app.py avant chaque opération)
_current_user_id = None

def set_user(user_id: str):
    """Définit l'utilisateur courant pour toutes les opérations."""
    global _current_user_id
    _current_user_id = user_id

def get_user():
    return _current_user_id

# ============================================================
# CONFIG
# ============================================================

def charger_config() -> dict:
    """Charge la config depuis Supabase si disponible, sinon fichier local."""
    if SUPABASE_OK and _current_user_id:
        try:
            res = _db.table("config_utilisateur") \
                     .select("cle,valeur") \
                     .eq("user_id", _current_user_id) \
                     .execute()
            if res.data:
                return {row["cle"]: row["valeur"] for row in res.data}
        except Exception:
            pass
    # Fallback fichier local
    return _charger_config_local()

def sauvegarder_config(config: dict):
    """Sauvegarde la config dans Supabase si disponible, sinon fichier local."""
    if SUPABASE_OK and _current_user_id:
        try:
            for cle, valeur in config.items():
                _db.table("config_utilisateur").upsert({
                    "user_id": _current_user_id,
                    "cle": cle,
                    "valeur": str(valeur) if valeur is not None else "",
                    "updated_at": "now()"
                }, on_conflict="user_id,cle").execute()
            return
        except Exception:
            pass
    # Fallback fichier local
    _sauvegarder_config_local(config)

# ============================================================
# HISTORIQUE
# ============================================================

def charger_historique() -> dict:
    """Charge l'historique depuis Supabase si disponible, sinon fichier local."""
    if SUPABASE_OK and _current_user_id:
        try:
            res = _db.table("historique_veille") \
                     .select("sujet,date_session,articles,resume_global") \
                     .eq("user_id", _current_user_id) \
                     .order("created_at", desc=True) \
                     .execute()
            if res.data is not None:
                historique = {}
                for row in res.data:
                    sujet = row["sujet"]
                    if sujet not in historique:
                        historique[sujet] = []
                    historique[sujet].append({
                        "date":          row["date_session"],
                        "articles":      row["articles"] or [],
                        "resume_global": row.get("resume_global", ""),
                    })
                return historique
        except Exception:
            pass
    # Fallback fichier local
    return _charger_historique_local()

def sauvegarder_historique(historique: dict):
    """Sauvegarde l'historique dans Supabase si disponible, sinon fichier local."""
    if SUPABASE_OK and _current_user_id:
        try:
            # Supprime l'ancien historique de cet utilisateur et réinsère
            _db.table("historique_veille") \
               .delete() \
               .eq("user_id", _current_user_id) \
               .execute()

            rows = []
            for sujet, sessions in historique.items():
                if sujet.startswith("__") or not isinstance(sessions, list):
                    continue
                for session in sessions:
                    if not isinstance(session, dict):
                        continue
                    rows.append({
                        "user_id":       _current_user_id,
                        "sujet":         sujet,
                        "date_session":  session.get("date", ""),
                        "articles":      session.get("articles", []),
                        "resume_global": session.get("resume_global", ""),
                    })
            if rows:
                _db.table("historique_veille").insert(rows).execute()
            return
        except Exception:
            pass
    # Fallback fichier local
    _sauvegarder_historique_local(historique)

def effacer_historique():
    """Efface tout l'historique de l'utilisateur courant."""
    if SUPABASE_OK and _current_user_id:
        try:
            _db.table("historique_veille") \
               .delete() \
               .eq("user_id", _current_user_id) \
               .execute()
            return
        except Exception:
            pass
    _sauvegarder_historique_local({})

# ============================================================
# FALLBACK — fichiers locaux (pour tests en local)
# ============================================================

def _get_app_dir():
    racine = os.environ.get("VEILLE_RACINE", "")
    if not racine:
        if os.access("/tmp", os.W_OK):
            racine = "/tmp"
        else:
            racine = os.path.dirname(os.path.abspath(__file__))
    app = os.path.join(racine, ".app")
    os.makedirs(app, exist_ok=True)
    return app

def _charger_config_local() -> dict:
    try:
        with open(os.path.join(_get_app_dir(), "config.json"), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _sauvegarder_config_local(config: dict):
    try:
        path = os.path.join(_get_app_dir(), "config.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def _charger_historique_local() -> dict:
    try:
        with open(os.path.join(_get_app_dir(), "historique_veille.json"), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _sauvegarder_historique_local(h: dict):
    try:
        path = os.path.join(_get_app_dir(), "historique_veille.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(h, f, ensure_ascii=False, indent=2)
    except Exception:
        pass