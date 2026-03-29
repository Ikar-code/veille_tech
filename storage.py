# ============================================================
# STORAGE.PY — Persistance Supabase isolée par utilisateur
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
            if res.data:
                return {row["cle"]: row["valeur"] for row in res.data}
            return {}
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
# HISTORIQUE (par utilisateur)
# ============================================================

def charger_historique() -> dict:
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
            return {}
        except Exception:
            pass
    return _charger_historique_local()

def sauvegarder_historique(historique: dict):
    if SUPABASE_OK and _current_user_id:
        try:
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
    _sauvegarder_historique_local(historique)

def effacer_historique():
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
# VEILLE AUTOMATIQUE (par utilisateur)
# ============================================================

def charger_veille_auto(user_id=None) -> dict:
    """Charge les préférences de veille automatique d'un utilisateur."""
    uid = user_id or _current_user_id
    if not SUPABASE_OK or not uid:
        return {}
    try:
        res = _db.table("veille_auto") \
                 .select("*") \
                 .eq("user_id", uid) \
                 .execute()
        if res.data:
            return res.data[0]
        return {}
    except Exception:
        return {}

def sauvegarder_veille_auto(sujets: str, heure: int, minute: int, actif: bool, user_id=None):
    """Sauvegarde les préférences de veille automatique."""
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
    """Met à jour la date de dernière exécution."""
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
    """
    Retourne la liste des utilisateurs dont la veille doit tourner maintenant.
    Appelé par cron.py toutes les heures.
    """
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
    """Récupère l'email d'un utilisateur."""
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
    """Charge la config d'un utilisateur spécifique (pour cron)."""
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

def charger_historique_utilisateur(user_id: str) -> dict:
    """Charge l'historique d'un utilisateur spécifique (pour cron)."""
    if not SUPABASE_OK:
        return {}
    try:
        res = _db.table("historique_veille") \
                 .select("sujet,date_session,articles,resume_global") \
                 .eq("user_id", user_id) \
                 .order("created_at", desc=True) \
                 .execute()
        historique = {}
        for row in res.data or []:
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
        return {}

def sauvegarder_historique_utilisateur(user_id: str, historique: dict):
    """Sauvegarde l'historique d'un utilisateur spécifique (pour cron)."""
    if not SUPABASE_OK:
        return
    try:
        _db.table("historique_veille").delete().eq("user_id", user_id).execute()
        rows = []
        for sujet, sessions in historique.items():
            if sujet.startswith("__") or not isinstance(sessions, list):
                continue
            for session in sessions:
                if not isinstance(session, dict):
                    continue
                rows.append({
                    "user_id":       user_id,
                    "sujet":         sujet,
                    "date_session":  session.get("date", ""),
                    "articles":      session.get("articles", []),
                    "resume_global": session.get("resume_global", ""),
                })
        if rows:
            _db.table("historique_veille").insert(rows).execute()
    except Exception as e:
        print(f"Erreur sauvegarder_historique_utilisateur : {e}")

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