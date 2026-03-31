# ============================================================
# AUTH.PY — Authentification Supabase (connexion lazy)
# ============================================================

import os

# Connexion lazy — on ne se connecte qu'au premier appel
_supabase       = None
_supabase_admin = None

def _get_client():
    """Client public (auth utilisateur)."""
    global _supabase
    if _supabase is None:
        from supabase import create_client
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_ANON_KEY", "")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL ou SUPABASE_ANON_KEY manquant")
        _supabase = create_client(url, key)
    return _supabase

def _get_admin():
    """Client admin (lecture/écriture sans restrictions)."""
    global _supabase_admin
    if _supabase_admin is None:
        from supabase import create_client
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_SERVICE_KEY", "")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL ou SUPABASE_SERVICE_KEY manquant")
        _supabase_admin = create_client(url, key)
    return _supabase_admin

RECHERCHES_GRATUITES = 1

# ============================================================
# INSCRIPTION / CONNEXION
# ============================================================

def inscrire(email: str, password: str) -> dict:
    try:
        res = _get_client().auth.sign_up({"email": email, "password": password})
        if res.user:
            try:
                admin = _get_admin()
                admin.table("users").insert({
                    "id": res.user.id,
                    "email": email,
                    "is_subscribed": False,
                }).execute()
                admin.table("search_quota").insert({
                    "user_id": res.user.id,
                    "searches_used": 0,
                }).execute()
            except Exception:
                pass
            return {"ok": True, "message": "Compte créé ! Vérifiez votre email."}
        return {"ok": False, "message": "Erreur lors de la création du compte."}
    except Exception as e:
        msg = str(e)
        if "already registered" in msg:
            return {"ok": False, "message": "Email déjà utilisé."}
        return {"ok": False, "message": f"Erreur : {msg}"}


def connecter(email: str, password: str) -> dict:
    try:
        res = _get_client().auth.sign_in_with_password({"email": email, "password": password})
        if res.user:
            return {"ok": True, "user": res.user, "session": res.session}
        return {"ok": False, "message": "Identifiants incorrects."}
    except Exception as e:
        return {"ok": False, "message": f"Erreur : {str(e)}"}


def connecter_google() -> str:
    try:
        res = _get_client().auth.sign_in_with_oauth({
            "provider": "google",
            "options": {"redirect_to": os.getenv("APP_URL", "http://localhost:8501")}
        })
        return res.url
    except Exception:
        return None


def deconnecter():
    try:
        _get_client().auth.sign_out()
    except Exception:
        pass


def reinitialiser_mot_de_passe(email: str) -> dict:
    try:
        _get_client().auth.reset_password_email(email)
        return {"ok": True, "message": "Email de réinitialisation envoyé."}
    except Exception as e:
        return {"ok": False, "message": str(e)}

# ============================================================
# PROFIL UTILISATEUR
# ============================================================

def get_profil(user_id: str) -> dict:
    try:
        res = _get_admin().table("users").select("*").eq("id", user_id).single().execute()
        return res.data or {}
    except Exception:
        return {}


def est_abonne(user_id: str) -> bool:
    from datetime import datetime, timezone
    try:
        profil = get_profil(user_id)
        if not profil.get("is_subscribed"):
            return False
        fin = profil.get("subscription_end")
        if fin:
            try:
                fin_dt = datetime.fromisoformat(str(fin).replace("Z", "+00:00"))
                if fin_dt.tzinfo is None:
                    fin_dt = fin_dt.replace(tzinfo=timezone.utc)
                return fin_dt > datetime.now(timezone.utc)
            except Exception:
                return False
        return True
    except Exception:
        return False

# ============================================================
# QUOTA RECHERCHES
# ============================================================

def get_quota(user_id: str) -> dict:
    try:
        res = _get_admin().table("search_quota").select("*").eq("user_id", user_id).single().execute()
        return res.data or {"searches_used": 0}
    except Exception:
        return {"searches_used": 0}


def peut_rechercher(user_id: str) -> tuple:
    if est_abonne(user_id):
        return True, ""
    quota = get_quota(user_id)
    used  = quota.get("searches_used", 0)
    if used >= RECHERCHES_GRATUITES:
        return False, (
            f"Vous avez utilisé votre {RECHERCHES_GRATUITES} recherche gratuite. "
            "Abonnez-vous à 2,99€/mois pour un accès illimité."
        )
    return True, ""


def incrementer_quota(user_id: str):
    try:
        quota   = get_quota(user_id)
        nouveau = quota.get("searches_used", 0) + 1
        _get_admin().table("search_quota").update({
            "searches_used": nouveau
        }).eq("user_id", user_id).execute()
    except Exception:
        pass

# ============================================================
# MISE À JOUR ABONNEMENT (webhook Stripe)
# ============================================================

def activer_abonnement(stripe_customer_id: str, fin_timestamp: int):
    from datetime import datetime, timezone
    fin = datetime.fromtimestamp(fin_timestamp, tz=timezone.utc).isoformat()
    try:
        _get_admin().table("users").update({
            "is_subscribed": True,
            "subscription_end": fin,
        }).eq("stripe_customer_id", stripe_customer_id).execute()
    except Exception as e:
        print(f"Erreur activation abonnement : {e}")


def desactiver_abonnement(stripe_customer_id: str):
    try:
        _get_admin().table("users").update({
            "is_subscribed": False,
        }).eq("stripe_customer_id", stripe_customer_id).execute()
    except Exception as e:
        print(f"Erreur désactivation abonnement : {e}")


def lier_stripe(user_id: str, stripe_customer_id: str):
    try:
        _get_admin().table("users").update({
            "stripe_customer_id": stripe_customer_id
        }).eq("id", user_id).execute()
    except Exception as e:
        print(f"Erreur liaison Stripe : {e}")