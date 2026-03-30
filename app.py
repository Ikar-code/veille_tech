# ============================================================
# APP.PY — Veille IA — corrigé
# ============================================================

import streamlit as st
import os
from datetime import datetime
from urllib.parse import urlparse

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

import serveur as srv

AUTH_OK = False
try:
    import auth
    AUTH_OK = True
except Exception:
    pass

STORAGE_OK = False
try:
    import storage
    STORAGE_OK = True
except Exception:
    pass

# ============================================================
# CONFIG STREAMLIT
# ============================================================
st.set_page_config(
    page_title="Veille IA",
    page_icon="🔭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# CSS
# ============================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');
:root {
    --bg:#1e1e2e;--surface:#181825;--overlay:#313244;
    --text:#cdd6f4;--subtext:#a6adc8;
    --blue:#89b4fa;--yellow:#f9e2af;--green:#a6e3a1;
    --red:#f38ba8;--mauve:#cba6f7;--border:#45475a;
}
.stApp{background:var(--bg);font-family:'DM Sans',sans-serif;color:var(--text);}
.stApp>header{background:transparent!important;}
[data-testid="stSidebar"]{background:var(--surface)!important;border-right:1px solid var(--border);}
[data-testid="stSidebar"] .stMarkdown h2{font-family:'Space Mono',monospace;font-size:13px;color:var(--blue);letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid var(--border);padding-bottom:8px;margin-bottom:12px;}
h1,h2,h3{font-family:'Space Mono',monospace!important;color:var(--text)!important;}
h1{font-size:22px!important;letter-spacing:1px;}
h3{font-size:14px!important;color:var(--subtext)!important;font-weight:400!important;}
.stTextInput>div>div>input,.stTextArea textarea,.stNumberInput input{background:var(--overlay)!important;border:1px solid var(--border)!important;color:var(--text)!important;border-radius:8px!important;font-family:'DM Sans',sans-serif!important;}
.stTextInput>div>div>input:focus,.stTextArea textarea:focus{border-color:var(--blue)!important;box-shadow:0 0 0 2px rgba(137,180,250,.15)!important;}
.stButton>button{background:var(--overlay)!important;color:var(--text)!important;border:1px solid var(--border)!important;border-radius:8px!important;font-weight:500!important;transition:all .15s ease!important;padding:.5rem 1.2rem!important;}
.stButton>button:hover{background:var(--blue)!important;color:var(--bg)!important;border-color:var(--blue)!important;}
.stTabs [data-baseweb="tab-list"]{background:var(--surface);border-radius:10px;padding:4px;gap:4px;border-bottom:none!important;}
.stTabs [data-baseweb="tab"]{background:transparent!important;color:var(--subtext)!important;border-radius:8px!important;font-size:13px!important;padding:8px 16px!important;border:none!important;}
.stTabs [aria-selected="true"]{background:var(--overlay)!important;color:var(--blue)!important;}
.card{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:20px;margin-bottom:12px;}
.card-accent{border-left:3px solid var(--blue);}
.card-green{border-left:3px solid var(--green);}
.card-red{border-left:3px solid var(--red);}
.card-mauve{border-left:3px solid var(--mauve);}
.metric-box{background:var(--overlay);border-radius:10px;padding:16px 20px;text-align:center;}
.metric-val{font-family:'Space Mono',monospace;font-size:28px;font-weight:700;color:var(--blue);display:block;}
.metric-lbl{font-size:11px;color:var(--subtext);text-transform:uppercase;letter-spacing:1px;margin-top:4px;display:block;}
.badge{display:inline-block;padding:2px 10px;border-radius:20px;font-size:11px;font-weight:600;}
.badge-green{background:rgba(166,227,161,.15);color:var(--green);border:1px solid var(--green);}
.badge-red{background:rgba(243,139,168,.15);color:var(--red);border:1px solid var(--red);}
.badge-yellow{background:rgba(249,226,175,.15);color:var(--yellow);border:1px solid var(--yellow);}
.badge-blue{background:rgba(137,180,250,.15);color:var(--blue);border:1px solid var(--blue);}
.badge-mauve{background:rgba(203,166,247,.15);color:var(--mauve);border:1px solid var(--mauve);}
.log-box{background:#0d0d1a;border:1px solid var(--border);border-radius:8px;padding:14px 16px;font-family:'Space Mono',monospace;font-size:12px;color:#a6e3a1;max-height:220px;overflow-y:auto;line-height:1.7;}
.abonnement-box{background:var(--surface);border:1px solid var(--mauve);border-radius:16px;padding:32px;text-align:center;margin:20px 0;}
hr{border-color:var(--border)!important;margin:16px 0!important;}
#MainMenu,footer,.stDeployButton{display:none!important;}
::-webkit-scrollbar{width:6px;}
::-webkit-scrollbar-track{background:var(--surface);}
::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px;}
.stSelectbox div[data-baseweb="select"]>div{background:var(--overlay)!important;border-color:var(--border)!important;color:var(--text)!important;border-radius:8px!important;}
.stNumberInput [data-baseweb="input"]{background:var(--overlay)!important;border-color:var(--border)!important;}
.streamlit-expanderHeader{background:var(--surface)!important;border-radius:8px!important;color:var(--text)!important;}
</style>
""", unsafe_allow_html=True)

# ============================================================
# SESSION STATE
# ============================================================
def _init_state():
    defaults = {
        "resultats":[],"sujet_courant":"","logs":[],
        "en_cours":False,"page":"veille",
        "user":None,"session":None,"profil":{},
        "show_auth":False,
    }
    for k,v in defaults.items():
        if k not in st.session_state:
            st.session_state[k]=v

_init_state()

# ============================================================
# HELPERS
# ============================================================
def _log(msg):
    h=datetime.now().strftime("%H:%M:%S")
    st.session_state["logs"].append(f"[{h}] {msg}")
    if len(st.session_state["logs"])>120:
        st.session_state["logs"]=st.session_state["logs"][-100:]

def _badge(label,style="blue"):
    return f'<span class="badge badge-{style}">{label}</span>'

def _user_id():
    u=st.session_state.get("user")
    return u.id if u else None

def _est_abonne():
    if not AUTH_OK: return False
    uid=_user_id()
    return auth.est_abonne(uid) if uid else False

def _goto(page):
    st.session_state["page"]=page
    st.rerun()

def _activer_storage(user_id):
    if STORAGE_OK and user_id:
        storage.set_user(user_id)
        srv.charger_historique     = storage.charger_historique
        srv.sauvegarder_historique = storage.sauvegarder_historique
        srv.charger_config         = storage.charger_config
        srv.sauvegarder_config     = storage.sauvegarder_config

def _cfg():
    return storage.charger_config() if STORAGE_OK else srv.charger_config()

def _save_cfg(c):
    if STORAGE_OK: storage.sauvegarder_config(c)
    else: srv.sauvegarder_config(c)

def _historique():
    return storage.charger_historique() if STORAGE_OK else srv.charger_historique()

def _effacer():
    if STORAGE_OK: storage.effacer_historique()
    else: srv.effacer_historique()

def _compteurs():
    h=_historique()
    nb_s=sum(1 for k in h if not k.startswith("__"))
    nb_a=sum(len(s.get("articles",[]))for ss in h.values() if isinstance(ss,list) for s in ss if isinstance(s,dict))
    return nb_s,nb_a

# ============================================================
# SIDEBAR UNIQUE
# ============================================================
def render_sidebar():
    user   = st.session_state.get("user")
    page   = st.session_state["page"]
    abonne = _est_abonne()

    with st.sidebar:
        st.markdown("## 🔭 Veille IA")
        st.markdown("---")

        # Bloc utilisateur
        if user:
            email = user.email if user else "?"
            st.markdown(
                f'<div style="padding:12px;background:var(--overlay);border-radius:10px;margin-bottom:12px;">'
                f'<div style="font-size:11px;color:var(--subtext);margin-bottom:3px;">Connecté</div>'
                f'<div style="font-size:12px;font-weight:500;word-break:break-all;">{email}</div>'
                f'<div style="margin-top:6px;">'
                f'{"<span class=\'badge badge-mauve\'>✨ Abonné</span>" if abonne else "<span class=\'badge badge-yellow\'>Gratuit</span>"}'
                f'</div></div>', unsafe_allow_html=True
            )
            if not abonne:
                st.markdown(
                    '<div style="background:rgba(203,166,247,.08);border:1px solid var(--mauve);'
                    'border-radius:10px;padding:10px;margin-bottom:12px;text-align:center;">'
                    '<div style="font-size:11px;color:var(--mauve);font-weight:600;margin-bottom:3px;">Passer à illimité</div>'
                    '<div style="font-size:20px;font-weight:700;">2,99€'
                    '<span style="font-size:11px;font-weight:400;color:var(--subtext)">/mois</span></div>'
                    '</div>', unsafe_allow_html=True
                )
        else:
            st.markdown(
                '<div style="background:rgba(137,180,250,.08);border:1px solid var(--blue);'
                'border-radius:10px;padding:12px;margin-bottom:12px;text-align:center;">'
                '<div style="font-size:12px;color:var(--subtext);margin-bottom:8px;">Connectez-vous pour accéder à toutes les fonctionnalités</div>'
                '</div>', unsafe_allow_html=True
            )
            if st.button("🔑 Se connecter", use_container_width=True, type="primary", key="sb_login"):
                st.session_state["show_auth"] = True
                st.rerun()

        st.markdown("---")
        st.markdown("## Navigation")

        # Pages selon état connexion
        if user:
            pages = {
                "🔍 Nouvelle veille": "veille",
                "📚 Historique":      "historique",
                "📊 Comparaison":     "comparaison",
                "⏰ Automatisation":  "auto",
                "⚙️ Configuration":   "config",
                "✨ Abonnement":      "abonnement",
            }
        else:
            pages = {
                "🔍 Nouvelle veille": "veille",
                "📚 Historique":      "historique",
                "📊 Comparaison":     "comparaison",
                "⚙️ Configuration":   "config",
            }

        for label, key in pages.items():
            actif = page == key
            if st.button(
                label,
                use_container_width=True,
                type="primary" if actif else "secondary",
                key=f"sb_nav_{key}"
            ):
                st.session_state["page"] = key
                st.session_state["show_auth"] = False
                st.rerun()

        st.markdown("---")

        if user:
            if st.button("🚪 Déconnexion", use_container_width=True, key="sb_logout"):
                auth.deconnecter()
                if STORAGE_OK: storage.set_user(None)
                st.session_state["user"]     = None
                st.session_state["session"]  = None
                st.session_state["profil"]   = {}
                st.session_state["page"]     = "veille"
                st.session_state["show_auth"]= False
                st.rerun()
        else:
            st.markdown(
                '<p style="font-size:11px;color:var(--subtext);text-align:center;">'
                'Veille auto · Groq · DuckDuckGo</p>',
                unsafe_allow_html=True
            )

# ============================================================
# PAGE AUTH
# ============================================================
def page_auth():
    col_l,col_c,col_r=st.columns([1,1.2,1])
    with col_c:
        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

        if st.button("← Retour", key="auth_back"):
            st.session_state["show_auth"] = False
            st.rerun()

        st.markdown(
            '<div style="text-align:center;margin:20px 0 32px 0;">'
            '<div style="font-family:Space Mono;font-size:24px;color:var(--blue);">🔭 Veille IA</div>'
            '<div style="font-size:13px;color:var(--subtext);margin-top:8px;">Connexion à votre espace</div>'
            '</div>', unsafe_allow_html=True
        )

        tab_co, tab_in = st.tabs(["Se connecter", "Créer un compte"])

        with tab_co:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            email = st.text_input("Email", key="login_email", placeholder="votre@email.com")
            pwd   = st.text_input("Mot de passe", type="password", key="login_pwd")

            if st.button("Se connecter", use_container_width=True, type="primary", key="btn_login"):
                if not email or not pwd:
                    st.error("Remplissez tous les champs.")
                else:
                    with st.spinner("Connexion…"):
                        res = auth.connecter(email, pwd)
                    if res["ok"]:
                        st.session_state["user"]     = res["user"]
                        st.session_state["session"]  = res["session"]
                        st.session_state["profil"]   = auth.get_profil(res["user"].id)
                        st.session_state["show_auth"]= False
                        st.session_state["page"]     = "veille"
                        _activer_storage(res["user"].id)
                        st.rerun()
                    else:
                        st.error(res["message"])

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            if st.button("Mot de passe oublié ?", use_container_width=True, key="btn_reset"):
                if email:
                    res = auth.reinitialiser_mot_de_passe(email)
                    st.success(res["message"]) if res["ok"] else st.error(res["message"])
                else:
                    st.warning("Entrez votre email d'abord.")

            st.markdown("---")
            if st.button("🔵 Continuer avec Google", use_container_width=True, key="btn_google"):
                url = auth.connecter_google()
                if url:
                    st.markdown(f'<meta http-equiv="refresh" content="0;url={url}">', unsafe_allow_html=True)
                else:
                    st.error("Google OAuth non configuré.")

        with tab_in:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            st.markdown(
                '<div class="card card-green" style="padding:14px 16px;margin-bottom:16px;">'
                '<div style="font-size:13px;font-weight:600;color:var(--green);margin-bottom:6px;">Offre gratuite</div>'
                '<div style="font-size:12px;color:var(--subtext);line-height:1.8;">'
                '✔ 1 recherche offerte<br>✔ Accès à l\'historique<br>✔ Sans carte bancaire'
                '</div></div>', unsafe_allow_html=True
            )
            email2 = st.text_input("Email", key="reg_email", placeholder="votre@email.com")
            pwd2   = st.text_input("Mot de passe", type="password", key="reg_pwd", help="Minimum 6 caractères")
            pwd2b  = st.text_input("Confirmer", type="password", key="reg_pwd2")
            st.markdown('<div style="font-size:11px;color:var(--subtext);margin:8px 0;">En créant un compte vous acceptez nos CGU.</div>', unsafe_allow_html=True)

            if st.button("Créer mon compte", use_container_width=True, type="primary", key="btn_register"):
                if not email2 or not pwd2:
                    st.error("Remplissez tous les champs.")
                elif pwd2 != pwd2b:
                    st.error("Les mots de passe ne correspondent pas.")
                elif len(pwd2) < 6:
                    st.error("Minimum 6 caractères.")
                else:
                    with st.spinner("Création…"):
                        res = auth.inscrire(email2, pwd2)
                    if res["ok"]:
                        st.success(res["message"])
                        st.info("Vérifiez votre email puis connectez-vous.")
                    else:
                        st.error(res["message"])

# ============================================================
# PAGE AUTOMATISATION
# ============================================================
def page_auto():
    st.markdown("# ⏰ Veille automatique")
    st.markdown("### Recevez votre veille par email chaque jour à l'heure de votre choix")
    st.markdown("---")

    if not AUTH_OK or not _user_id():
        st.warning("Connectez-vous pour configurer la veille automatique.")
        return

    abonne = _est_abonne()
    if not abonne:
        st.markdown(
            '<div class="card card-mauve" style="padding:24px;text-align:center;">'
            '<div style="font-size:20px;margin-bottom:8px;">🔒</div>'
            '<div style="font-size:16px;font-weight:600;color:var(--mauve);margin-bottom:8px;">Fonctionnalité Premium</div>'
            '<div style="font-size:13px;color:var(--subtext);">La veille automatique par email est réservée aux abonnés.</div>'
            '</div>', unsafe_allow_html=True
        )
        if st.button("✨ S'abonner à 2,99€/mois", type="primary"):
            _goto("abonnement")
        return

    uid   = _user_id()
    prefs = storage.charger_veille_auto(uid) if STORAGE_OK else {}

    st.markdown('<div class="card card-accent">', unsafe_allow_html=True)
    st.markdown("#### Configurer votre veille automatique")

    sujets = st.text_area(
        "Sujets de veille (séparés par des virgules)",
        value=prefs.get("sujets",""),
        placeholder="ex: intelligence artificielle, cybersécurité, LLM",
        height=80
    )

    st.markdown("#### Heure d'envoi")
    st.markdown(
        '<div style="font-size:12px;color:var(--subtext);margin-bottom:12px;">'
        'La Réunion = UTC+4 · France = UTC+1 (hiver) / UTC+2 (été)'
        '</div>', unsafe_allow_html=True
    )

    col1, col2, col3 = st.columns([1,1,2])
    with col1:
        heure_utc = st.selectbox("Heure (UTC)", list(range(24)),
                                  index=int(prefs.get("heure",4)),
                                  format_func=lambda h: f"{h:02d}h")
    with col2:
        opts = [0,15,30,45]
        min_val = int(prefs.get("minute",0))
        min_idx = opts.index(min_val) if min_val in opts else 0
        minute_utc = st.selectbox("Minute", opts, index=min_idx,
                                   format_func=lambda m: f"{m:02d}")
    with col3:
        h_reunion = (heure_utc+4)%24
        st.markdown(
            f'<div class="metric-box" style="margin-top:20px;">'
            f'<span class="metric-val" style="font-size:20px;">{h_reunion:02d}h{minute_utc:02d}</span>'
            f'<span class="metric-lbl">Heure Réunion (UTC+4)</span>'
            f'</div>', unsafe_allow_html=True
        )

    actif = st.toggle("Activer la veille automatique", value=bool(prefs.get("actif", True)))
    st.markdown("</div>", unsafe_allow_html=True)

    if prefs.get("derniere_execution"):
        try:
            from datetime import timezone as tz
            d = datetime.fromisoformat(str(prefs["derniere_execution"]).replace("Z","+00:00"))
            st.markdown(
                f'<div style="font-size:12px;color:var(--subtext);margin-top:8px;">'
                f'Dernière exécution : {d.strftime("%d/%m/%Y à %H:%M")} UTC</div>',
                unsafe_allow_html=True
            )
        except Exception:
            pass

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    if st.button("💾 Enregistrer", type="primary"):
        if not sujets.strip():
            st.error("Entrez au moins un sujet.")
        elif STORAGE_OK:
            ok = storage.sauvegarder_veille_auto(sujets.strip(), int(heure_utc), int(minute_utc), actif, uid)
            if ok:
                st.success(f"✅ Veille {'activée' if actif else 'désactivée'} — envoi à {h_reunion:02d}h{minute_utc:02d} (Réunion)" if actif else "Veille désactivée.")
            else:
                st.error("Erreur Supabase.")

    st.markdown("---")
    st.markdown(
        '<div class="card" style="padding:16px;">'
        '<div style="font-size:13px;font-weight:600;margin-bottom:8px;">Comment ça fonctionne</div>'
        '<div style="font-size:12px;color:var(--subtext);line-height:1.9;">'
        '1. Un robot tourne automatiquement sur nos serveurs toutes les heures<br>'
        '2. À l\'heure choisie, il lance la recherche sur vos sujets<br>'
        '3. Il génère les résumés IA et vous envoie un email<br>'
        '4. Vous n\'avez rien à faire — tout se passe sans connexion'
        '</div></div>', unsafe_allow_html=True
    )

# ============================================================
# PAGE ABONNEMENT
# ============================================================
def page_abonnement():
    st.markdown("# ✨ Abonnement")
    st.markdown("---")
    if _est_abonne():
        st.markdown(
            '<div class="card card-green" style="padding:24px;text-align:center;">'
            '<div style="font-size:32px;margin-bottom:8px;">✅</div>'
            '<div style="font-size:18px;font-weight:600;color:var(--green);margin-bottom:8px;">Abonnement actif</div>'
            '<div style="font-size:13px;color:var(--subtext);">Recherches illimitées + veille email quotidienne.</div>'
            '</div>', unsafe_allow_html=True
        )
        st.info("Pour annuler, contactez support@veille-ia.fr")
    else:
        col_l,col_c,col_r=st.columns([1,1.5,1])
        with col_c:
            stripe_url=os.getenv("STRIPE_PAYMENT_LINK","")
            st.markdown(
                '<div class="abonnement-box">'
                '<div style="font-size:13px;color:var(--mauve);font-weight:600;letter-spacing:2px;text-transform:uppercase;margin-bottom:16px;">Veille IA Premium</div>'
                '<div style="font-size:48px;font-weight:700;">2,99€</div>'
                '<div style="font-size:14px;color:var(--subtext);margin-bottom:24px;">par mois · sans engagement</div>'
                '<div style="text-align:left;margin-bottom:24px;font-size:13px;line-height:2;">'
                '✔ Recherches illimitées<br>✔ Veille automatique par email<br>'
                '✔ Historique complet<br>✔ Résumés IA par article<br>✔ Comparaison entre sessions'
                '</div></div>', unsafe_allow_html=True
            )
            if stripe_url:
                st.markdown(
                    f'<a href="{stripe_url}" target="_blank" style="display:block;text-align:center;'
                    f'background:var(--mauve);color:#1e1e2e;font-weight:700;font-size:15px;'
                    f'padding:14px;border-radius:10px;text-decoration:none;">'
                    f'✨ S\'abonner — 2,99€/mois</a>', unsafe_allow_html=True
                )
            else:
                st.warning("Paiement Stripe disponible prochainement.")

# ============================================================
# PAGE VEILLE
# ============================================================
def page_veille():
    st.markdown("# 🔍 Nouvelle veille")
    st.markdown("### Recherche, scoring et publication automatique")
    st.markdown("---")

    uid    = _user_id()
    abonne = _est_abonne()

    if AUTH_OK and uid:
        if not abonne:
            quota = auth.get_quota(uid)
            reste = max(0, auth.RECHERCHES_GRATUITES - quota.get("searches_used",0))
            if reste == 0:
                st.markdown(
                    '<div class="card card-red" style="padding:24px;text-align:center;">'
                    '<div style="font-size:20px;margin-bottom:8px;">🔒</div>'
                    '<div style="font-size:16px;font-weight:600;color:var(--red);margin-bottom:8px;">Limite gratuite atteinte</div>'
                    '<div style="font-size:13px;color:var(--subtext);">Abonnez-vous pour un accès illimité.</div>'
                    '</div>', unsafe_allow_html=True
                )
                if st.button("✨ S'abonner à 2,99€/mois", type="primary"):
                    _goto("abonnement")
                return
            st.markdown(f'<div style="margin-bottom:16px;">{_badge(f"Compte gratuit · {reste} recherche(s) restante(s)","yellow")}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="margin-bottom:16px;">{_badge("✨ Abonné · Recherches illimitées","mauve")}</div>', unsafe_allow_html=True)

    col_form, col_log = st.columns([1,1], gap="large")
    with col_form:
        st.markdown('<div class="card card-accent">', unsafe_allow_html=True)
        sujet  = st.text_area("Sujets de recherche", placeholder="ex: cybersécurité IA, deepfake, LLM Europe", height=90)
        c1, c2 = st.columns(2)
        with c1: limite = st.number_input("Articles max", min_value=1, max_value=50, value=10, step=1)
        with c2: mode   = st.selectbox("Mode", ["Mise à jour page","Créer un post"])
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1: lancer = st.button("▶ Lancer", use_container_width=True, disabled=st.session_state["en_cours"], type="primary")
        with c2:
            if st.button("🗑 Logs", use_container_width=True):
                st.session_state["logs"] = []
                st.rerun()

        if st.session_state["resultats"]:
            st.markdown("---")
            nb_r = len(st.session_state["resultats"])
            st.markdown(f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;"><span style="font-family:Space Mono;font-size:13px;">Résultats</span>{_badge(f"{nb_r} articles","green")}</div>', unsafe_allow_html=True)
            for r in st.session_state["resultats"][:8]:
                dom   = urlparse(r.get("href","")).netloc
                score = r.get("score",0)
                c     = "green" if score>=80 else "yellow" if score>=50 else "red"
                st.markdown(
                    f'<div class="card" style="padding:12px 16px;margin-bottom:6px;">'
                    f'<div style="font-size:13px;font-weight:500;margin-bottom:4px;">{r.get("title","")[:72]}…</div>'
                    f'<div style="display:flex;gap:8px;">'
                    f'<span style="font-size:11px;color:var(--subtext)">{dom}</span>'
                    f'{_badge(f"score {score}",c)}</div></div>', unsafe_allow_html=True
                )

    with col_log:
        st.markdown('<div style="font-family:Space Mono;font-size:12px;color:var(--subtext);text-transform:uppercase;letter-spacing:1px;margin-bottom:10px;">— Journal</div>', unsafe_allow_html=True)
        log_html = "<br>".join(st.session_state["logs"][-40:] if st.session_state["logs"] else ["<span style='color:var(--subtext)'>En attente…</span>"])
        st.markdown(f'<div class="log-box">{log_html}</div>', unsafe_allow_html=True)
        if st.session_state["en_cours"]:
            st.progress(0.0, text="Traitement…")

    if lancer and sujet.strip() and not st.session_state["en_cours"]:
        if AUTH_OK and uid:
            ok_q, msg_q = auth.peut_rechercher(uid)
            if not ok_q:
                st.error(msg_q)
                return
        st.session_state["en_cours"]     = True
        st.session_state["resultats"]    = []
        st.session_state["sujet_courant"]= sujet.strip()
        st.session_state["logs"]         = []
        _log(f"Démarrage — {sujet.strip()}")
        try:
            resultats = srv.rechercher(sujet.strip(), callback_statut=_log)
            st.session_state["resultats"] = resultats
            _log(f"✅ {len(resultats)} résultats")
            if AUTH_OK and uid and not abonne:
                auth.incrementer_quota(uid)
            if mode == "Mise à jour page":
                res = srv.workflow_publier(sujet.strip(), resultats, callback_statut=_log, limite=int(limite))
                for canal,(ok,msg) in res.items():
                    _log(f"{'✅' if ok else '❌'} {canal.upper()} : {msg}")
            else:
                ok, msg = srv.workflow_creer_post(sujet.strip(), resultats[:int(limite)], callback_statut=_log)
                _log(f"{'✅' if ok else '❌'} Post : {msg}")
        except Exception as e:
            _log(f"❌ Erreur : {e}")
        st.session_state["en_cours"] = False
        st.rerun()
    elif lancer and not sujet.strip():
        st.warning("Entrez au moins un sujet.")

# ============================================================
# PAGE HISTORIQUE
# ============================================================
def page_historique():
    st.markdown("# 📚 Historique des veilles")
    st.markdown("---")
    h = _historique()
    sujets = [k for k in h if not k.startswith("__") and isinstance(h[k],list)]
    if not sujets:
        st.info("Aucun historique. Lancez une première veille.")
        return
    col_g, col_d = st.columns([1,2], gap="large")
    with col_g:
        sujet_sel = st.selectbox("Sujet", sujets)
        sessions  = h.get(sujet_sel,[])
        st.markdown(f'<div class="metric-box" style="margin:12px 0;"><span class="metric-val">{len(sessions)}</span><span class="metric-lbl">Sessions</span></div>', unsafe_allow_html=True)
        if st.button("🗑 Effacer", type="secondary", use_container_width=True):
            _effacer()
            st.success("Effacé.")
            st.rerun()
    with col_d:
        for i, session in enumerate(sessions):
            if not isinstance(session,dict): continue
            date_s   = session.get("date","?")
            articles = session.get("articles",[])
            rg       = session.get("resume_global","")
            with st.expander(f"📅 {date_s} — {len(articles)} articles", expanded=(i==0)):
                if rg and not rg.startswith("Erreur"):
                    st.markdown(
                        f'<div class="card" style="border-left:3px solid var(--yellow);margin-bottom:16px;">'
                        f'<div style="font-size:12px;font-weight:600;color:var(--yellow);margin-bottom:8px;">SYNTHÈSE</div>'
                        f'<div style="font-size:13px;line-height:1.7;">{rg[:1200]}…</div></div>',
                        unsafe_allow_html=True
                    )
                for a in sorted(articles, key=lambda x: x.get("score",0), reverse=True):
                    dom    = urlparse(a.get("href","")).netloc
                    score  = a.get("score",0)
                    points = a.get("resume_ollama",[])
                    pts_html = ""
                    if points and points != ["Contenu non accessible pour ce site."]:
                        pts_html = "".join(f'<li style="font-size:12px;color:var(--subtext);margin:3px 0">{p}</li>' for p in points[:3])
                        pts_html = f"<ul style='padding-left:18px;margin:6px 0 0 0'>{pts_html}</ul>"
                    st.markdown(
                        f'<div class="card" style="padding:12px 16px;margin-bottom:6px;">'
                        f'<div style="display:flex;justify-content:space-between;">'
                        f'<a href="{a.get("href","")}" target="_blank" style="color:var(--blue);font-size:13px;font-weight:500">{a.get("title","")[:80]}</a>'
                        f'<span class="badge badge-blue">{score}</span></div>'
                        f'<div style="font-size:11px;color:var(--subtext);margin-top:4px">{dom}</div>'
                        f'{pts_html}</div>', unsafe_allow_html=True
                    )

# ============================================================
# PAGE COMPARAISON
# ============================================================
def page_comparaison():
    st.markdown("# 📊 Comparaison de sessions")
    st.markdown("---")
    h = _historique()
    sujets = [k for k in h if not k.startswith("__") and isinstance(h[k],list)]
    if not sujets:
        st.info("Aucun historique.")
        return
    sujet_sel = st.selectbox("Sujet", sujets)
    sessions  = [s for s in h.get(sujet_sel,[]) if isinstance(s,dict)]
    if len(sessions) < 2:
        st.warning("Il faut au moins 2 sessions.")
        return
    dates = [s.get("date",f"Session {i+1}") for i,s in enumerate(sessions)]
    c1, c2 = st.columns(2)
    with c1: date_rec = st.selectbox("Session récente", dates, index=0)
    with c2: date_anc = st.selectbox("Session précédente", dates, index=min(1,len(dates)-1))
    if date_rec == date_anc:
        st.warning("Choisissez deux sessions différentes.")
        return
    sess_rec = next((s for s in sessions if s.get("date")==date_rec), None)
    sess_anc = next((s for s in sessions if s.get("date")==date_anc), None)
    if not sess_rec or not sess_anc:
        st.error("Sessions introuvables.")
        return
    hrefs_anc = {a["href"] for a in sess_anc.get("articles",[]) if "href" in a}
    hrefs_rec = {a["href"] for a in sess_rec.get("articles",[]) if "href" in a}
    nouveaux  = hrefs_rec - hrefs_anc
    disparus  = hrefs_anc - hrefs_rec
    c1, c2, c3 = st.columns(3)
    for col,val,lbl,clr in [(c1,len(sess_rec.get("articles",[])),"Récents","blue"),(c2,len(nouveaux),"Nouveaux","green"),(c3,len(disparus),"Disparus","red")]:
        with col:
            st.markdown(f'<div class="metric-box"><span class="metric-val" style="color:var(--{clr})">{val}</span><span class="metric-lbl">{lbl}</span></div>', unsafe_allow_html=True)
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    if st.button("🧠 Générer l'analyse", type="primary"):
        with st.spinner("Analyse IA…"):
            try:
                analyse = srv.comparer_sessions(sujet_sel, sess_rec, sess_anc)
                st.markdown(
                    f'<div class="card card-accent" style="margin-top:16px;">'
                    f'<div style="font-size:12px;font-weight:600;color:var(--mauve);margin-bottom:12px;">ANALYSE COMPARATIVE</div>'
                    f'<div style="font-size:13px;line-height:1.8;white-space:pre-line">{analyse}</div></div>',
                    unsafe_allow_html=True
                )
            except Exception as e:
                st.error(f"Erreur : {e}")

# ============================================================
# PAGE CONFIG
# ============================================================
def page_config():
    st.markdown("# ⚙️ Configuration")
    st.markdown("---")
    cfg = _cfg()
    tab_wp, tab_ftp = st.tabs(["🌐 WordPress","📡 FTP"])
    with tab_wp:
        st.markdown("#### Connexion WordPress")
        wp_base = st.text_input("URL du site", value=cfg.get("wp_base",""), placeholder="https://monsite.com")
        c1, c2  = st.columns(2)
        with c1: wp_user = st.text_input("Identifiant", value=cfg.get("wp_user",""))
        with c2: wp_pwd  = st.text_input("Mot de passe app", value=cfg.get("wp_password",""), type="password")
        cs, ct  = st.columns(2)
        with cs:
            if st.button("💾 Sauvegarder", use_container_width=True):
                cfg.update({"wp_base":wp_base,"wp_user":wp_user,"wp_password":wp_pwd})
                _save_cfg(cfg)
                st.success("Sauvegardé !")
        with ct:
            if st.button("🔌 Tester", use_container_width=True):
                ok, msg = srv.tester_connexion_wp(wp_base, wp_user, wp_pwd)
                st.success(msg) if ok else st.error(msg)
    with tab_ftp:
        st.markdown("#### Connexion FTP")
        ftp_host = st.text_input("Hôte FTP", value=cfg.get("ftp_host",""))
        c1, c2   = st.columns(2)
        with c1: ftp_user = st.text_input("Utilisateur FTP", value=cfg.get("ftp_user",""))
        with c2: ftp_pwd  = st.text_input("Mot de passe FTP", value=cfg.get("ftp_password",""), type="password")
        ftp_path = st.text_input("Chemin distant", value=cfg.get("ftp_path","/htdocs/veille-ia.html"))
        cs, ct   = st.columns(2)
        with cs:
            if st.button("💾 Sauvegarder FTP", use_container_width=True):
                cfg.update({"ftp_host":ftp_host,"ftp_user":ftp_user,"ftp_password":ftp_pwd,"ftp_path":ftp_path})
                _save_cfg(cfg)
                st.success("Sauvegardé !")
        with ct:
            if st.button("🔌 Tester FTP", use_container_width=True):
                ok, msg = srv.tester_connexion_ftp(ftp_host, ftp_user, ftp_pwd)
                st.success(msg) if ok else st.error(msg)
    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        mode_s = "Supabase ☁️" if (STORAGE_OK and storage.SUPABASE_OK) else "Fichier local 💾"
        st.markdown(f'<div class="card"><div style="font-size:11px;color:var(--subtext)">Stockage</div><div style="font-size:13px;font-weight:500;margin-top:4px">{mode_s}</div></div>', unsafe_allow_html=True)
    with c2:
        nb_s, nb_a = _compteurs()
        st.markdown(f'<div class="card"><div style="font-size:12px;color:var(--subtext)">Historique</div><div style="font-size:12px;margin-top:4px">{nb_s} sujets · {nb_a} articles</div></div>', unsafe_allow_html=True)

# ============================================================
# ROUTING PRINCIPAL — une seule sidebar, logique claire
# ============================================================
user = st.session_state.get("user")

# Réactive le storage si déjà connecté
if user and STORAGE_OK:
    _activer_storage(user.id)

# Sidebar unique (toujours affichée)
render_sidebar()

# Contenu principal
page        = st.session_state["page"]
show_auth   = st.session_state.get("show_auth", False)

if show_auth or (AUTH_OK and not user and page in ["auto","abonnement"]):
    page_auth()
elif page == "veille":
    page_veille()
elif page == "historique":
    page_historique()
elif page == "comparaison":
    page_comparaison()
elif page == "auto":
    page_auto()
elif page == "config":
    page_config()
elif page == "abonnement":
    page_abonnement()
else:
    page_veille()