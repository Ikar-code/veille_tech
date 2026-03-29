# ============================================================
# AUTH.PY — Authentification Supabase
# Tables : users (id, email, is_subscribed, stripe_customer_id, subscription_end)
#          search_quota (id, user_id, searches_used, last_reset)
# ============================================================

import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
REDIRECT_URL = os.getenv("SUPABASE_GOOGLE_REDIRECT", "")

# Nombre de recherches gratuites avant blocage
RECHERCHES_GRATUITES = 1

# ── Client Supabase ────────────────────────────────────────
try:
    from supabase import create_client, Client
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("SUPABASE_URL ou SUPABASE_KEY manquant dans .env")
    _supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as _e:
    raise ImportError(f"Impossible d'initialiser Supabase : {_e}")


# ============================================================
# INSCRIPTION
# ============================================================
def inscrire(email: str, password: str) -> dict:
    try:
        res = _supabase.auth.sign_up({"email": email, "password": password})
        if res.user:
            uid = res.user.id
            # Insérer dans users
            try:
                _supabase.table("users").insert({
                    "id":            uid,
                    "email":         email,
                    "is_subscribed": False,
                }).execute()
            except Exception:
                pass
            # Insérer dans search_quota
            try:
                _supabase.table("search_quota").insert({
                    "user_id":       uid,
                    "searches_used": 0,
                }).execute()
            except Exception:
                pass
            return {"ok": True, "message": "Compte créé ! Vérifiez votre email.", "user": res.user}
        return {"ok": False, "message": "Échec de l'inscription. Réessayez.", "user": None}
    except Exception as e:
        msg = str(e)
        if "already registered" in msg or "already been registered" in msg:
            return {"ok": False, "message": "Cet email est déjà utilisé.", "user": None}
        return {"ok": False, "message": f"Erreur : {msg}", "user": None}


# ============================================================
# CONNEXION EMAIL / MOT DE PASSE
# ============================================================
def connecter(email: str, password: str) -> dict:
    try:
        res = _supabase.auth.sign_in_with_password({"email": email, "password": password})
        if res.user and res.session:
            _assurer_search_quota(res.user.id)
            return {"ok": True, "message": "Connecté.", "user": res.user, "session": res.session}
        return {"ok": False, "message": "Identifiants incorrects.", "user": None, "session": None}
    except Exception as e:
        msg = str(e)
        if "Invalid login" in msg or "invalid_grant" in msg:
            return {"ok": False, "message": "Email ou mot de passe incorrect.", "user": None, "session": None}
        if "Email not confirmed" in msg:
            return {"ok": False, "message": "Confirmez votre email avant de vous connecter.", "user": None, "session": None}
        return {"ok": False, "message": f"Erreur : {msg}", "user": None, "session": None}


# ============================================================
# CONNEXION GOOGLE (OAuth)
# ============================================================
def connecter_google() -> str | None:
    """Retourne l'URL OAuth Google, ou None si non configuré."""
    try:
        params = {"provider": "google"}
        if REDIRECT_URL:
            params["options"] = {"redirect_to": REDIRECT_URL.rstrip("/") + "/"}
        res = _supabase.auth.sign_in_with_oauth(params)
        return res.url if res and res.url else None
    except Exception:
        return None


# ============================================================
# DÉCONNEXION
# ============================================================
def deconnecter() -> None:
    try:
        _supabase.auth.sign_out()
    except Exception:
        pass


# ============================================================
# RÉINITIALISATION MOT DE PASSE
# ============================================================
def reinitialiser_mot_de_passe(email: str) -> dict:
    try:
        opts = {}
        if REDIRECT_URL:
            opts["redirect_to"] = REDIRECT_URL.rstrip("/") + "/reset"
        _supabase.auth.reset_password_email(email, opts if opts else None)
        return {"ok": True, "message": f"Email envoyé à {email}. Vérifiez votre boîte."}
    except Exception as e:
        return {"ok": False, "message": f"Erreur : {e}"}


# ============================================================
# PROFIL (table users)
# ============================================================
def get_profil(user_id: str) -> dict:
    """Récupère la ligne dans users. Crée si absente."""
    try:
        res = _supabase.table("users").select("*").eq("id", user_id).single().execute()
        return res.data or {}
    except Exception:
        try:
            _supabase.table("users").insert({
                "id":            user_id,
                "is_subscribed": False,
            }).execute()
        except Exception:
            pass
        return {"id": user_id, "is_subscribed": False}


# ============================================================
# ABONNEMENT (table users : is_subscribed, subscription_end)
# ============================================================
def est_abonne(user_id: str) -> bool:
    """Vérifie is_subscribed. Désactive automatiquement si subscription_end dépassé."""
    if not user_id:
        return False
    try:
        profil = get_profil(user_id)
        if not profil.get("is_subscribed", False):
            return False
        sub_end = profil.get("subscription_end")
        if sub_end:
            from datetime import datetime, timezone
            fin = datetime.fromisoformat(sub_end.replace("Z", "+00:00"))
            if fin < datetime.now(timezone.utc):
                _supabase.table("users").update({"is_subscribed": False}).eq("id", user_id).execute()
                return False
        return True
    except Exception:
        return False


def activer_abonnement(user_id: str, stripe_customer_id: str = "", subscription_end=None) -> bool:
    try:
        data = {"is_subscribed": True}
        if stripe_customer_id:
            data["stripe_customer_id"] = stripe_customer_id
        if subscription_end:
            data["subscription_end"] = subscription_end
        _supabase.table("users").update(data).eq("id", user_id).execute()
        return True
    except Exception:
        return False


def desactiver_abonnement(user_id: str) -> bool:
    try:
        _supabase.table("users").update({"is_subscribed": False}).eq("id", user_id).execute()
        return True
    except Exception:
        return False


# ============================================================
# QUOTA (table search_quota)
# ============================================================
def _assurer_search_quota(user_id: str) -> None:
    """Crée la ligne search_quota si elle n'existe pas encore."""
    try:
        res = _supabase.table("search_quota").select("id").eq("user_id", user_id).execute()
        if not res.data:
            _supabase.table("search_quota").insert({
                "user_id":       user_id,
                "searches_used": 0,
            }).execute()
    except Exception:
        pass


def get_quota(user_id: str) -> dict:
    """Retourne {"searches_used": int, "abonne": bool}"""
    try:
        res = _supabase.table("search_quota").select("*").eq("user_id", user_id).single().execute()
        quota = res.data or {}
    except Exception:
        quota = {}
    return {
        "searches_used": quota.get("searches_used", 0),
        "abonne":        est_abonne(user_id),
    }


def peut_rechercher(user_id: str) -> tuple[bool, str]:
    """Vérifie si l'utilisateur peut lancer une recherche."""
    if est_abonne(user_id):
        return True, ""
    quota = get_quota(user_id)
    used  = quota.get("searches_used", 0)
    if used < RECHERCHES_GRATUITES:
        return True, ""
    return (
        False,
        f"Limite gratuite atteinte ({RECHERCHES_GRATUITES} recherche). "
        "Abonnez-vous pour un accès illimité."
    )


def incrementer_quota(user_id: str) -> None:
    """Incrémente searches_used dans search_quota."""
    try:
        res = _supabase.table("search_quota").select("id, searches_used").eq("user_id", user_id).single().execute()
        if res.data:
            nouveau = res.data.get("searches_used", 0) + 1
            _supabase.table("search_quota").update(
                {"searches_used": nouveau}
            ).eq("user_id", user_id).execute()
        else:
            _supabase.table("search_quota").insert(
                {"user_id": user_id, "searches_used": 1}
            ).execute()
    except Exception:
        pass