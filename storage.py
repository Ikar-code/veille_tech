# ============================================================
# STORAGE.PY — VERSION FINALE (SAFE + SCALABLE)
# - Isolation utilisateur SÉCURISÉE
# - Compatible multi-user (Render)
# - Historique en base (pas JSON global)
# - user_id prioritaire (anti fuite)
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

# ============================================================
# USER CONTEXT (SAFE)
# ============================================================

_uid_courant = None

def set_user(user_id):
    global _uid_courant
    _uid_courant = user_id

def _uid(user_id=None):
    uid = user_id or _uid_courant
    if not uid:
        raise ValueError("Aucun user_id fourni.")
    return uid

# ============================================================
# CONFIG
# ============================================================

def charger_config(user_id=None) -> dict:
    if SUPABASE_OK:
        try:
            uid = _uid(user_id)
            res = _db.table("config_utilisateur") \
                     .select("cle,valeur") \
                     .eq("user_id", uid) \
                     .execute()
            return {row["cle"]: row["valeur"] for row in res.data} if res.data else {}
        except Exception:
            pass
    return {}

def sauvegarder_config(config: dict, user_id=None):
    if SUPABASE_OK:
        try:
            uid = _uid(user_id)
            for cle, valeur in config.items():
                _db.table("config_utilisateur").upsert({
                    "user_id": uid,
                    "cle": str(cle),
                    "valeur": str(valeur) if valeur is not None else "",
                }, on_conflict="user_id,cle").execute()
            return
        except Exception as e:
            print("Erreur config:", e)

# ============================================================
# HISTORIQUE (STRUCTURÉ + FUSION)
# ============================================================

def charger_historique(user_id=None) -> dict:
    if not SUPABASE_OK:
        return {}

    try:
        uid = _uid(user_id)

        res = _db.table("historique_veille") \
                 .select("id,sujet,date_session,articles,resume_global") \
                 .eq("user_id", uid) \
                 .order("created_at", desc=True) \
                 .execute()

        historique = {}

        for row in res.data or []:
            sujet = row["sujet"]

            if sujet not in historique:
                historique[sujet] = []

            historique[sujet].append({
                "_db_id": row["id"],
                "date": row["date_session"],
                "articles": row["articles"] or [],
                "resume_global": row.get("resume_global", "")
            })

        return historique

    except Exception as e:
        print("Erreur chargement historique:", e)
        return {}

def sauvegarder_historique(historique: dict, user_id=None):
    if not SUPABASE_OK:
        return

    try:
        uid = _uid(user_id)

        # Charger existant
        existant = charger_historique(uid)

        index = {}
        for sujet, sessions in existant.items():
            for s in sessions:
                key = (sujet, s.get("date"))
                index[key] = s.get("_db_id")

        for sujet, sessions in historique.items():
            if not isinstance(sessions, list):
                continue

            for s in sessions:
                date = s.get("date")
                articles = s.get("articles", [])
                resume = s.get("resume_global", "")

                key = (sujet, date)

                if key in index:
                    # UPDATE
                    _db.table("historique_veille").update({
                        "articles": articles,
                        "resume_global": resume
                    }).eq("id", index[key]).execute()
                else:
                    # INSERT
                    _db.table("historique_veille").insert({
                        "user_id": uid,
                        "sujet": sujet,
                        "date_session": date,
                        "articles": articles,
                        "resume_global": resume
                    }).execute()

    except Exception as e:
        print("Erreur sauvegarde historique:", e)

def effacer_historique(user_id=None):
    if not SUPABASE_OK:
        return

    try:
        uid = _uid(user_id)
        _db.table("historique_veille") \
           .delete() \
           .eq("user_id", uid) \
           .execute()
    except Exception:
        pass

# ============================================================
# VEILLE AUTO
# ============================================================

def charger_veille_auto(user_id=None) -> dict:
    try:
        uid = _uid(user_id)
        res = _db.table("veille_auto") \
                 .select("*") \
                 .eq("user_id", uid) \
                 .execute()
        return res.data[0] if res.data else {}
    except Exception:
        return {}

def sauvegarder_veille_auto(sujets, heure, minute, actif, user_id=None) -> bool:
    try:
        uid = _uid(user_id)
        _db.table("veille_auto").upsert({
            "user_id": uid,
            "sujets": sujets,
            "heure": heure,
            "minute": minute,
            "actif": actif
        }, on_conflict="user_id").execute()
        return True
    except Exception as e:
        print("Erreur veille auto:", e)
        return False

def marquer_execution(user_id):
    try:
        from datetime import datetime, timezone
        _db.table("veille_auto").update({
            "derniere_execution": datetime.now(timezone.utc).isoformat()
        }).eq("user_id", user_id).execute()
    except Exception:
        pass

def lister_utilisateurs_a_notifier(heure_utc, minute_utc):
    try:
        res = _db.table("veille_auto") \
                 .select("user_id,sujets") \
                 .eq("actif", True) \
                 .eq("heure", heure_utc) \
                 .eq("minute", minute_utc) \
                 .execute()
        return res.data or []
    except Exception:
        return []

def get_user_email(user_id):
    try:
        res = _db.table("users") \
                 .select("email") \
                 .eq("id", user_id) \
                 .single() \
                 .execute()
        return res.data.get("email", "")
    except Exception:
        return ""

# ============================================================
# CHAT — Mémoire persistante par utilisateur
# ============================================================

def charger_historique_chat(user_id: str, limite: int = 40) -> list:
    """Charge les N derniers messages du chat pour un utilisateur."""
    if not SUPABASE_OK or not user_id:
        return []
    try:
        res = _db.table("chat_historique") \
                 .select("role,content") \
                 .eq("user_id", user_id) \
                 .order("created_at", desc=False) \
                 .limit(limite) \
                 .execute()
        return [{"role": r["role"], "content": r["content"]} for r in (res.data or [])]
    except Exception as e:
        print(f"Erreur charger_historique_chat : {e}")
        return []

def sauvegarder_message_chat(user_id: str, role: str, content: str) -> bool:
    """Sauvegarde un message dans l'historique chat."""
    if not SUPABASE_OK or not user_id:
        return False
    try:
        _db.table("chat_historique").insert({
            "user_id": user_id,
            "role":    role,
            "content": content,
        }).execute()
        return True
    except Exception as e:
        print(f"Erreur sauvegarder_message_chat : {e}")
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
        print(f"Erreur effacer_historique_chat : {e}")
        return False
