# ============================================================
# STORAGE.PY — Persistance Supabase par utilisateur
# ============================================================

import os
import json
from datetime import datetime

SUPABASE_URL     = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE = os.environ.get("SUPABASE_SERVICE_KEY", "") or os.environ.get("SUPABASE_ANON_KEY", "")

SUPABASE_OK = False
_db = None

try:
    from supabase import create_client
    if SUPABASE_URL and SUPABASE_SERVICE:
        _db = create_client(SUPABASE_URL, SUPABASE_SERVICE)
        SUPABASE_OK = True
except Exception as e:
    print(f"[storage] Supabase indisponible : {e}")

# ── Utilisateur courant ────────────────────────────────────
_current_user_id = None

def set_user(user_id):
    global _current_user_id
    _current_user_id = user_id

def get_user():
    return _current_user_id


# ============================================================
# CONFIG
# ============================================================

def charger_config() -> dict:
    if not SUPABASE_OK or not _current_user_id:
        return {}
    try:
        res = _db.table("config_utilisateur") \
                 .select("cle,valeur") \
                 .eq("user_id", _current_user_id) \
                 .execute()
        return {r["cle"]: r["valeur"] for r in (res.data or [])}
    except Exception as e:
        print(f"[storage] charger_config : {e}")
        return {}

def sauvegarder_config(config: dict):
    if not SUPABASE_OK or not _current_user_id:
        return
    try:
        for cle, valeur in config.items():
            _db.table("config_utilisateur").upsert({
                "user_id": _current_user_id,
                "cle":     cle,
                "valeur":  str(valeur),
                "updated_at": datetime.utcnow().isoformat(),
            }, on_conflict="user_id,cle").execute()
    except Exception as e:
        print(f"[storage] sauvegarder_config : {e}")

def charger_config_utilisateur(user_id: str) -> dict:
    """Version explicite avec user_id (pour le cron)."""
    if not SUPABASE_OK or not user_id:
        return {}
    try:
        res = _db.table("config_utilisateur") \
                 .select("cle,valeur") \
                 .eq("user_id", user_id) \
                 .execute()
        return {r["cle"]: r["valeur"] for r in (res.data or [])}
    except Exception as e:
        print(f"[storage] charger_config_utilisateur : {e}")
        return {}


# ============================================================
# HISTORIQUE VEILLE
# ============================================================

def charger_historique() -> dict:
    if not SUPABASE_OK or not _current_user_id:
        return {}
    try:
        res = _db.table("historique_veille") \
                 .select("sujet,date_session,articles,resume_global") \
                 .eq("user_id", _current_user_id) \
                 .order("date_session", desc=True) \
                 .execute()
        historique = {}
        for row in (res.data or []):
            sujet    = (row.get("sujet") or "").strip().lower()
            articles = row.get("articles") or []
            if isinstance(articles, str):
                try: articles = json.loads(articles)
                except Exception: articles = []
            session = {
                "date":          row.get("date_session",""),
                "articles":      articles,
                "resume_global": row.get("resume_global",""),
            }
            historique.setdefault(sujet, []).append(session)
        # Trie les sessions par date (plus récente en premier)
        for sujet in historique:
            historique[sujet].sort(
                key=lambda s: s.get("date",""), reverse=True)
        return historique
    except Exception as e:
        print(f"[storage] charger_historique : {e}")
        return {}

def sauvegarder_historique(historique: dict):
    if not SUPABASE_OK or not _current_user_id:
        return
    try:
        for sujet, sessions in historique.items():
            if sujet.startswith("__") or not isinstance(sessions, list):
                continue
            for session in sessions:
                if not isinstance(session, dict):
                    continue
                date_s   = session.get("date","")
                articles = session.get("articles",[])
                rg       = session.get("resume_global","")
                if not date_s:
                    continue
                _db.table("historique_veille").upsert({
                    "user_id":       _current_user_id,
                    "sujet":         sujet.strip().lower(),
                    "date_session":  date_s,
                    "articles":      json.dumps(articles, ensure_ascii=False),
                    "resume_global": rg,
                }, on_conflict="user_id,sujet,date_session").execute()
    except Exception as e:
        print(f"[storage] sauvegarder_historique : {e}")

def effacer_historique():
    if not SUPABASE_OK or not _current_user_id:
        return
    try:
        _db.table("historique_veille") \
           .delete() \
           .eq("user_id", _current_user_id) \
           .execute()
    except Exception as e:
        print(f"[storage] effacer_historique : {e}")


# ============================================================
# VEILLE AUTO — avec intervalle_jours
# ============================================================

def charger_veille_auto(user_id: str) -> dict:
    if not SUPABASE_OK or not user_id:
        return {}
    try:
        res = _db.table("veille_auto") \
                 .select("*") \
                 .eq("user_id", user_id) \
                 .limit(1) \
                 .execute()
        data = (res.data or [])
        return data[0] if data else {}
    except Exception as e:
        print(f"[storage] charger_veille_auto : {e}")
        return {}

def sauvegarder_veille_auto(sujets: str, heure: int, minute: int,
                             actif: bool, user_id: str,
                             intervalle_jours: int = 1) -> bool:
    """
    Sauvegarde la configuration de veille automatique.
    intervalle_jours : 1=chaque jour, 2=tous les 2 jours, 7=hebdo, 30=mensuel…
    """
    if not SUPABASE_OK or not user_id:
        return False
    try:
        _db.table("veille_auto").upsert({
            "user_id":          user_id,
            "sujets":           sujets,
            "heure":            heure,
            "minute":           minute,
            "actif":            actif,
            "intervalle_jours": max(1, int(intervalle_jours)),
        }, on_conflict="user_id").execute()
        return True
    except Exception as e:
        print(f"[storage] sauvegarder_veille_auto : {e}")
        return False

def marquer_execution(user_id: str):
    if not SUPABASE_OK or not user_id:
        return
    try:
        _db.table("veille_auto").update({
            "derniere_execution": datetime.utcnow().isoformat()
        }).eq("user_id", user_id).execute()
    except Exception as e:
        print(f"[storage] marquer_execution : {e}")

def lister_utilisateurs_a_notifier(heure: int, minute: int) -> list:
    """
    Retourne les utilisateurs dont la veille est active ET
    dont l'heure correspond ET dont l'intervalle est écoulé
    depuis la dernière exécution.
    """
    if not SUPABASE_OK:
        return []
    try:
        res = _db.table("veille_auto") \
                 .select("user_id,sujets,derniere_execution,intervalle_jours") \
                 .eq("actif",  True) \
                 .eq("heure",  heure) \
                 .eq("minute", minute) \
                 .execute()
        utilisateurs_a_traiter = []
        maintenant = datetime.utcnow()

        for row in (res.data or []):
            intervalle = int(row.get("intervalle_jours") or 1)
            derniere   = row.get("derniere_execution")

            # Jamais exécuté → toujours traiter
            if not derniere:
                utilisateurs_a_traiter.append(row)
                continue

            try:
                dt_derniere = datetime.fromisoformat(
                    str(derniere).replace("Z","+00:00").replace("+00:00",""))
                jours_ecoules = (maintenant - dt_derniere).days
                if jours_ecoules >= intervalle:
                    utilisateurs_a_traiter.append(row)
            except Exception:
                # Date invalide → traiter quand même
                utilisateurs_a_traiter.append(row)

        return utilisateurs_a_traiter
    except Exception as e:
        print(f"[storage] lister_utilisateurs_a_notifier : {e}")
        return []

def get_user_email(user_id: str) -> str:
    if not SUPABASE_OK or not user_id:
        return ""
    try:
        from supabase import create_client
        admin = create_client(SUPABASE_URL, SUPABASE_SERVICE)
        res   = admin.auth.admin.get_user_by_id(user_id)
        return res.user.email if res and res.user else ""
    except Exception as e:
        print(f"[storage] get_user_email : {e}")
        return ""


# ============================================================
# CHAT — Mémoire persistante par utilisateur
# ============================================================

def charger_historique_chat(user_id: str, limite: int = 40) -> list:
    """
    Charge les N derniers messages du chat pour un utilisateur.
    Retourne une liste de dict {"role": ..., "content": ...}.
    """
    if not SUPABASE_OK or not user_id:
        return []
    try:
        res = _db.table("chat_historique") \
                 .select("role,content") \
                 .eq("user_id", user_id) \
                 .order("created_at", desc=False) \
                 .limit(limite) \
                 .execute()
        return [{"role": r["role"], "content": r["content"]}
                for r in (res.data or [])]
    except Exception as e:
        print(f"[storage] charger_historique_chat : {e}")
        return []

def sauvegarder_message_chat(user_id: str, role: str, content: str) -> bool:
    """
    Sauvegarde un message (user ou assistant) dans l'historique chat.
    role doit être 'user' ou 'assistant'.
    """
    if not SUPABASE_OK or not user_id:
        return False
    if role not in ("user", "assistant"):
        return False
    try:
        _db.table("chat_historique").insert({
            "user_id": user_id,
            "role":    role,
            "content": content,
        }).execute()
        return True
    except Exception as e:
        print(f"[storage] sauvegarder_message_chat : {e}")
        return False

def effacer_historique_chat(user_id: str) -> bool:
    """Efface tout l'historique chat d'un utilisateur."""
    if not SUPABASE_OK or not user_id:
        return False
    try:
        _db.table("chat_historique") \
           .delete() \
           .eq("user_id", user_id) \
           .execute()
        return True
    except Exception as e:
        print(f"[storage] effacer_historique_chat : {e}")
        return False

def compter_messages_chat(user_id: str) -> int:
    """Retourne le nombre de messages stockés pour un utilisateur."""
    if not SUPABASE_OK or not user_id:
        return 0
    try:
        res = _db.table("chat_historique") \
                 .select("id", count="exact") \
                 .eq("user_id", user_id) \
                 .execute()
        return res.count or 0
    except Exception:
        return 0
