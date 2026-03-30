# ============================================================
# STORAGE.PY — Persistance Supabase isolée par utilisateur
# Fusion de l'historique (pas d'écrasement)
# ============================================================

import os
import json

try:
    from supabase import create_client
    _url = os.environ.get("SUPABASE_URL", "")
    _key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if _url and _key:
        _db = create_client(_url, _key)
        SUPABASE_OK = True
    else:
        _db = None
        SUPABASE_OK = False
except Exception:
    _db = None
    SUPABASE_OK = False

_current_user_id = None

def set_user(user_id):
    global _current_user_id
    _current_user_id = user_id

def get_user():
    return _current_user_id

# ============================================================
# CONFIG (par utilisateur)
# ============================================================

def charger_config() -> dict:
    if SUPABASE_OK and _current_user_id:
        try:
            res = _db.table("config_utilisateur") \
                     .select("cle,valeur") \
                     .eq("user_id", _current_user_id) \
                     .execute()
            return {row["cle"]: row["valeur"] for row in res.data} if res.data else {}
        except Exception:
            pass
    return _charger_config_local()

def sauvegarder_config(config: dict):
    if SUPABASE_OK and _current_user_id:
        try:
            for cle, valeur in config.items():
                _db.table("config_utilisateur").upsert({
                    "user_id": _current_user_id,
                    "cle": str(cle),
                    "valeur": str(valeur) if valeur is not None else "",
                }, on_conflict="user_id,cle").execute()
            return
        except Exception:
            pass
    _sauvegarder_config_local(config)

# ============================================================
# HISTORIQUE — FUSION (pas d'écrasement)
# ============================================================

def charger_historique() -> dict:
    """Charge l'historique de l'utilisateur courant."""
    if SUPABASE_OK and _current_user_id:
        return charger_historique_utilisateur(_current_user_id)
    return _charger_historique_local()

def sauvegarder_historique(historique: dict):
    """
    Sauvegarde l'historique en FUSIONNANT avec ce qui existe déjà.
    Ne supprime jamais les sessions existantes — ajoute ou met à jour.
    """
    if SUPABASE_OK and _current_user_id:
        sauvegarder_historique_utilisateur(_current_user_id, historique)
    else:
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
# HISTORIQUE UTILISATEUR SPÉCIFIQUE (pour cron)
# ============================================================

def charger_historique_utilisateur(user_id: str) -> dict:
    """Charge l'historique d'un utilisateur spécifique."""
    if not SUPABASE_OK or not user_id:
        return {}
    try:
        res = _db.table("historique_veille") \
                 .select("id,sujet,date_session,articles,resume_global") \
                 .eq("user_id", user_id) \
                 .order("created_at", desc=True) \
                 .execute()
        historique = {}
        for row in res.data or []:
            sujet = row["sujet"]
            if sujet not in historique:
                historique[sujet] = []
            historique[sujet].append({
                "_db_id":       row["id"],
                "date":         row["date_session"],
                "articles":     row["articles"] or [],
                "resume_global": row.get("resume_global", ""),
            })
        return historique
    except Exception as e:
        print(f"Erreur charger_historique_utilisateur : {e}")
        return {}

def sauvegarder_historique_utilisateur(user_id: str, historique: dict):
    """
    Sauvegarde l'historique d'un utilisateur en FUSIONNANT.
    - Si une session (sujet + date) existe déjà → on la met à jour
    - Si elle n'existe pas → on l'insère
    - On ne supprime jamais les sessions existantes
    """
    if not SUPABASE_OK or not user_id:
        return

    try:
        # Charge l'existant pour comparer
        existant = charger_historique_utilisateur(user_id)
        # Index par (sujet, date) → db_id
        index_existant = {}
        for sujet, sessions in existant.items():
            for s in sessions:
                key = (sujet, s.get("date", ""))
                index_existant[key] = s.get("_db_id")

        for sujet, sessions in historique.items():
            if sujet.startswith("__") or not isinstance(sessions, list):
                continue
            for session in sessions:
                if not isinstance(session, dict):
                    continue
                date_s  = session.get("date", "")
                articles = session.get("articles", [])
                resume  = session.get("resume_global", "")
                key     = (sujet, date_s)

                if key in index_existant and index_existant[key]:
                    # Met à jour la session existante
                    _db.table("historique_veille").update({
                        "articles":      articles,
                        "resume_global": resume,
                    }).eq("id", index_existant[key]).execute()
                else:
                    # Insère une nouvelle session
                    _db.table("historique_veille").insert({
                        "user_id":       user_id,
                        "sujet":         sujet,
                        "date_session":  date_s,
                        "articles":      articles,
                        "resume_global": resume,
                    }).execute()

    except Exception as e:
        print(f"Erreur sauvegarder_historique_utilisateur : {e}")

# ============================================================
# VEILLE AUTOMATIQUE
# ============================================================

def charger_veille_auto(user_id=None) -> dict:
    uid = user_id or _current_user_id
    if not SUPABASE_OK or not uid:
        return {}
    try:
        res = _db.table("veille_auto") \
                 .select("*") \
                 .eq("user_id", uid) \
                 .execute()
        return res.data[0] if res.data else {}
    except Exception:
        return {}

def sauvegarder_veille_auto(sujets: str, heure: int, minute: int, actif: bool, user_id=None) -> bool:
    uid = user_id or _current_user_id
    if not SUPABASE_OK or not uid:
        return False
    try:
        _db.table("veille_auto").upsert({
            "user_id": uid,
            "sujets":  sujets,
            "heure":   heure,
            "minute":  minute,
            "actif":   actif,
        }, on_conflict="user_id").execute()
        return True
    except Exception as e:
        print(f"Erreur sauvegarder_veille_auto : {e}")
        return False

def marquer_execution(user_id: str):
    if not SUPABASE_OK:
        return
    try:
        from datetime import datetime, timezone
        _db.table("veille_auto").update({
            "derniere_execution": datetime.now(timezone.utc).isoformat()
        }).eq("user_id", user_id).execute()
    except Exception:
        pass

def lister_utilisateurs_a_notifier(heure_utc: int, minute_utc: int) -> list:
    if not SUPABASE_OK:
        return []
    try:
        res = _db.table("veille_auto") \
                 .select("user_id,sujets,heure,minute") \
                 .eq("actif", True) \
                 .eq("heure", heure_utc) \
                 .eq("minute", minute_utc) \
                 .execute()
        return res.data or []
    except Exception as e:
        print(f"Erreur lister_utilisateurs_a_notifier : {e}")
        return []

def get_user_email(user_id: str) -> str:
    if not SUPABASE_OK:
        return ""
    try:
        res = _db.table("users") \
                 .select("email") \
                 .eq("id", user_id) \
                 .single() \
                 .execute()
        return res.data.get("email", "") if res.data else ""
    except Exception:
        return ""

def charger_config_utilisateur(user_id: str) -> dict:
    if not SUPABASE_OK:
        return {}
    try:
        res = _db.table("config_utilisateur") \
                 .select("cle,valeur") \
                 .eq("user_id", user_id) \
                 .execute()
        return {row["cle"]: row["valeur"] for row in res.data} if res.data else {}
    except Exception:
        return {}

# ============================================================
# FALLBACK LOCAL
# ============================================================

def _get_app_dir():
    racine = os.environ.get("VEILLE_RACINE", "")
    if not racine:
        racine = "/tmp" if os.access("/tmp", os.W_OK) else os.path.dirname(os.path.abspath(__file__))
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
        with open(os.path.join(_get_app_dir(), "config.json"), "w", encoding="utf-8") as f:
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
        with open(os.path.join(_get_app_dir(), "historique_veille.json"), "w", encoding="utf-8") as f:
            json.dump(h, f, ensure_ascii=False, indent=2)
    except Exception:
        pass