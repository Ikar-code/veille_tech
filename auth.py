# ============================================================
# AUTH.PY — Authentification Supabase — isolation par utilisateur
#
# PROBLÈME CORRIGÉ :
# Sur Render, tous les utilisateurs partagent le même processus Python.
# L'ancien code stockait la session dans un singleton global (_supabase),
# ce qui faisait que n'importe quel visiteur héritait de la session du
# dernier utilisateur connecté.
#
# SOLUTION :
# - _supabase (client public) est utilisé UNIQUEMENT pour les opérations
#   d'auth sans état (sign_up, sign_in, reset_password, oauth).
#   Il ne stocke aucune session utilisateur.
# - _supabase_admin (service role) est utilisé pour toutes les lectures/
#   écritures en base. Il n'a pas de notion d'utilisateur connecté.
# - La session utilisateur (access_token, refresh_token) est stockée
#   UNIQUEMENT dans st.session_state côté Streamlit, jamais dans un
#   singleton Python partagé.
# ============================================================

import os
import security

_supabase       = None   # client public — auth uniquement, jamais de session stockée
_supabase_admin = None   # client service_role — lecture/écriture DB


def _get_client():
    """Client public Supabase — opérations d'auth sans état uniquement."""
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
    """Client admin Supabase — toutes les opérations DB."""
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
    ok_email, msg_email = security.valider_email(email)
    if not ok_email:
        return {"ok": False, "message": msg_email}
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
    """
    Connexion standard email/mot de passe.
    Retourne user + session (access_token, refresh_token).
    Ces objets sont stockés dans st.session_state par app.py,
    JAMAIS dans un singleton global ici.
    """
    ok_email, msg_email = security.valider_email(email)
    if not ok_email:
        return {"ok": False, "message": msg_email}
    try:
        res = _get_client().auth.sign_in_with_password({"email": email, "password": password})
        if res.user:
            return {"ok": True, "user": res.user, "session": res.session}
        return {"ok": False, "message": "Identifiants incorrects."}
    except Exception as e:
        return {"ok": False, "message": f"Erreur : {str(e)}"}


def connecter_avec_refresh_token(refresh_token: str) -> dict:
    """
    Reconnexion automatique via le refresh_token stocké côté client
    (localStorage du navigateur). Ne touche pas au singleton global.
    Chaque appel crée une session temporaire isolée.
    """
    if not refresh_token or not refresh_token.strip():
        return {"ok": False, "message": "Token vide."}
    try:
        from supabase import create_client
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_ANON_KEY", "")
        if not url or not key:
            return {"ok": False, "message": "Config Supabase manquante."}
        # Client temporaire isolé — ne modifie pas le singleton global
        client_tmp = create_client(url, key)
        res = client_tmp.auth.refresh_session(refresh_token)
        session_obj = getattr(res, "session", res)
        user_obj    = getattr(session_obj, "user", None)
        if user_obj:
            return {"ok": True, "user": user_obj, "session": session_obj}
        return {"ok": False, "message": "Token expiré ou invalide."}
    except Exception as e:
        return {"ok": False, "message": f"Erreur refresh : {str(e)}"}


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
    """
    Déconnexion : on ne fait rien sur le client global car il ne stocke
    pas de session. La session est effacée dans st.session_state par app.py.
    """
    pass  # Rien à faire côté serveur — la session vit uniquement dans st.session_state


def reinitialiser_mot_de_passe(email: str) -> dict:
    ok_email, msg_email = security.valider_email(email)
    if not ok_email:
        return {"ok": False, "message": msg_email}
    try:
        _get_client().auth.reset_password_email(email)
        return {"ok": True, "message": "Email de réinitialisation envoyé."}
    except Exception as e:
        return {"ok": False, "message": str(e)}

# ============================================================
# PROFIL UTILISATEUR
# Toutes les lectures DB passent par _get_admin() (service role),
# qui ne dépend d'aucune session utilisateur.
# ============================================================

def get_profil(user_id: str) -> dict:
    if not user_id:
        return {}
    try:
        res = _get_admin().table("users").select("*").eq("id", user_id).single().execute()
        return res.data or {}
    except Exception:
        return {}


def accepter_conditions(user_id: str) -> dict:
    from datetime import datetime, timezone
    if not user_id:
        return {"ok": False, "message": "Utilisateur invalide."}
    try:
        _get_admin().table("users").update({
            "terms_accepted": True,
            "terms_accepted_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", user_id).execute()
        return {"ok": True, "message": "Conditions acceptées."}
    except Exception as e:
        return {"ok": False, "message": f"Erreur : {e}"}


def est_abonne(user_id: str) -> bool:
    from datetime import datetime, timezone
    if not user_id:
        return False
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
    if not user_id:
        return {"searches_used": 0}
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
    if not user_id:
        return
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