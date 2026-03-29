# ============================================================
# APP.PY — Interface Streamlit pour la veille technologique
# ============================================================

import streamlit as st
import json
import os
from datetime import datetime
from urllib.parse import urlparse

import serveur as srv

AUTH_OK = False
try:
    import auth
    AUTH_OK = True
except Exception:
    pass

st.set_page_config(
    page_title="Veille IA",
    page_icon="🔭",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');
:root {
    --bg: #1e1e2e; --surface: #181825; --overlay: #313244;
    --text: #cdd6f4; --subtext: #a6adc8;
    --blue: #89b4fa; --yellow: #f9e2af; --green: #a6e3a1;
    --red: #f38ba8; --mauve: #cba6f7; --border: #45475a;
}
.stApp { background: var(--bg); font-family: 'DM Sans', sans-serif; color: var(--text); }
.stApp > header { background: transparent !important; }
[data-testid="stSidebar"] { background: var(--surface) !important; border-right: 1px solid var(--border); }
[data-testid="stSidebar"] .stMarkdown h2 { font-family: 'Space Mono', monospace; font-size: 13px; color: var(--blue); letter-spacing: 2px; text-transform: uppercase; border-bottom: 1px solid var(--border); padding-bottom: 8px; margin-bottom: 12px; }
h1, h2, h3 { font-family: 'Space Mono', monospace !important; color: var(--text) !important; }
h1 { font-size: 22px !important; letter-spacing: 1px; }
h3 { font-size: 14px !important; color: var(--subtext) !important; font-weight: 400 !important; }
.stTextInput > div > div > input, .stTextArea textarea, .stNumberInput input { background: var(--overlay) !important; border: 1px solid var(--border) !important; color: var(--text) !important; border-radius: 8px !important; font-family: 'DM Sans', sans-serif !important; }
.stTextInput > div > div > input:focus, .stTextArea textarea:focus { border-color: var(--blue) !important; box-shadow: 0 0 0 2px rgba(137,180,250,0.15) !important; }
.stButton > button { background: var(--overlay) !important; color: var(--text) !important; border: 1px solid var(--border) !important; border-radius: 8px !important; font-family: 'DM Sans', sans-serif !important; font-weight: 500 !important; transition: all 0.15s ease !important; padding: 0.5rem 1.2rem !important; }
.stButton > button:hover { background: var(--blue) !important; color: var(--bg) !important; border-color: var(--blue) !important; }
.stTabs [data-baseweb="tab-list"] { background: var(--surface); border-radius: 10px; padding: 4px; gap: 4px; border-bottom: none !important; }
.stTabs [data-baseweb="tab"] { background: transparent !important; color: var(--subtext) !important; border-radius: 8px !important; font-family: 'DM Sans', sans-serif !important; font-size: 13px !important; padding: 8px 16px !important; border: none !important; }
.stTabs [aria-selected="true"] { background: var(--overlay) !important; color: var(--blue) !important; }
.card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 20px; margin-bottom: 12px; }
.card-accent { border-left: 3px solid var(--blue); }
.card-green  { border-left: 3px solid var(--green); }
.card-red    { border-left: 3px solid var(--red); }
.metric-box { background: var(--overlay); border-radius: 10px; padding: 16px 20px; text-align: center; }
.metric-val { font-family: 'Space Mono', monospace; font-size: 28px; font-weight: 700; color: var(--blue); display: block; }
.metric-lbl { font-size: 11px; color: var(--subtext); text-transform: uppercase; letter-spacing: 1px; margin-top: 4px; display: block; }
.badge { display: inline-block; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
.badge-green  { background: rgba(166,227,161,.15); color: var(--green);  border: 1px solid var(--green); }
.badge-red    { background: rgba(243,139,168,.15); color: var(--red);    border: 1px solid var(--red); }
.badge-yellow { background: rgba(249,226,175,.15); color: var(--yellow); border: 1px solid var(--yellow); }
.badge-blue   { background: rgba(137,180,250,.15); color: var(--blue);   border: 1px solid var(--blue); }
.badge-mauve  { background: rgba(203,166,247,.15); color: var(--mauve);  border: 1px solid var(--mauve); }
.log-box { background: #0d0d1a; border: 1px solid var(--border); border-radius: 8px; padding: 14px 16px; font-family: 'Space Mono', monospace; font-size: 12px; color: #a6e3a1; max-height: 220px; overflow-y: auto; line-height: 1.7; }
.abonnement-box { background: var(--surface); border: 1px solid var(--mauve); border-radius: 16px; padding: 32px; text-align: center; margin: 20px 0; }
hr { border-color: var(--border) !important; margin: 16px 0 !important; }
#MainMenu, footer, .stDeployButton { display: none !important; }
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: var(--surface); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
.stSelectbox div[data-baseweb="select"] > div { background: var(--overlay) !important; border-color: var(--border) !important; color: var(--text) !important; border-radius: 8px !important; }
.stNumberInput [data-baseweb="input"] { background: var(--overlay) !important; border-color: var(--border) !important; }
.streamlit-expanderHeader { background: var(--surface) !important; border-radius: 8px !important; color: var(--text) !important; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# SESSION STATE
# ============================================================
def _init_state():
    defaults = {
        "resultats": [], "sujet_courant": "", "logs": [],
        "en_cours": False, "onglet_actif": "veille",
        "user": None, "session": None, "profil": {},
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()

# ============================================================
# HELPERS
# ============================================================
def _log(msg):
    horodatage = datetime.now().strftime("%H:%M:%S")
    st.session_state["logs"].append(f"[{horodatage}] {msg}")
    if len(st.session_state["logs"]) > 120:
        st.session_state["logs"] = st.session_state["logs"][-100:]

def _badge_html(label, style="blue"):
    return f'<span class="badge badge-{style}">{label}</span>'

def _compteurs_historique():
    h = srv.charger_historique()
    nb_sujets   = sum(1 for k in h if not k.startswith("__"))
    nb_articles = sum(len(s.get("articles", [])) for sessions in h.values() if isinstance(sessions, list) for s in sessions if isinstance(s, dict))
    nb_sessions = sum(len(sessions) for sessions in h.values() if isinstance(sessions, list))
    return nb_sujets, nb_articles, nb_sessions

def _user_id():
    u = st.session_state.get("user")
    return u.id if u else None

def _est_abonne():
    if not AUTH_OK:
        return False
    uid = _user_id()
    return auth.est_abonne(uid) if uid else False

# ============================================================
# PAGE AUTH
# ============================================================
def page_auth():
    col_l, col_c, col_r = st.columns([1, 1.2, 1])
    with col_c:
        st.markdown("<div style='height:40px'></div>", unsafe_allow_html=True)
        st.markdown(
            '<div style="text-align:center;margin-bottom:32px;">'
            '<div style="font-family:Space Mono;font-size:24px;color:var(--blue);">🔭 Veille IA</div>'
            '<div style="font-size:13px;color:var(--subtext);margin-top:8px;">Plateforme de veille académique automatisée</div>'
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
                        st.session_state["user"]    = res["user"]
                        st.session_state["session"] = res["session"]
                        st.session_state["profil"]  = auth.get_profil(res["user"].id)
                        st.rerun()
                    else:
                        st.error(res["message"])

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            if st.button("Mot de passe oublié ?", use_container_width=True, key="btn_reset"):
                if email:
                    res = auth.reinitialiser_mot_de_passe(email)
                    if res["ok"]:
                        st.success(res["message"])
                    else:
                        st.error(res["message"])
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
                    else:
                        st.error(res["message"])

# ============================================================
# SIDEBAR connecté
# ============================================================
def sidebar_connecte():
    with st.sidebar:
        user   = st.session_state["user"]
        email  = user.email if user else "?"
        abonne = _est_abonne()

        st.markdown(
            f'<div style="padding:12px;background:var(--overlay);border-radius:10px;margin-bottom:16px;">'
            f'<div style="font-size:12px;color:var(--subtext);margin-bottom:4px;">Connecté</div>'
            f'<div style="font-size:13px;font-weight:500;word-break:break-all;">{email}</div>'
            f'<div style="margin-top:8px;">'
            f'{"<span class=\'badge badge-mauve\'>✨ Abonné</span>" if abonne else "<span class=\'badge badge-yellow\'>Gratuit</span>"}'
            f'</div></div>', unsafe_allow_html=True
        )

        # BUG FIX 1 : string mal fermée avec mélange de guillemets simples/doubles
        if not abonne:
            st.markdown(
                '<div style="background:rgba(203,166,247,.08);border:1px solid var(--mauve);'
                'border-radius:10px;padding:12px;margin-bottom:16px;text-align:center;">'
                '<div style="font-size:12px;color:var(--mauve);font-weight:600;margin-bottom:4px;">Passer à illimité</div>'
                '<div style="font-size:22px;font-weight:700;">2,99€<span style="font-size:12px;font-weight:400;color:var(--subtext)">/mois</span></div>'
                '</div>', unsafe_allow_html=True
            )
            if st.button("✨ S'abonner", use_container_width=True, key="btn_sub_side"):
                st.session_state["onglet_actif"] = "abonnement"
                st.rerun()

        st.markdown("---")
        st.markdown("## Navigation")
        pages = {
            "🔍 Nouvelle veille": "veille",
            "📚 Historique":      "historique",
            "📊 Comparaison":     "comparaison",
            "⚙️ Configuration":   "config",
            "✨ Abonnement":      "abonnement",
        }
        for label, key in pages.items():
            actif = st.session_state["onglet_actif"] == key
            if st.button(label, use_container_width=True,
                         type="primary" if actif else "secondary", key=f"nav_{key}"):
                st.session_state["onglet_actif"] = key
                st.rerun()

        st.markdown("---")
        if st.button("🚪 Déconnexion", use_container_width=True):
            auth.deconnecter()
            st.session_state["user"]    = None
            st.session_state["session"] = None
            st.session_state["profil"]  = {}
            st.session_state["onglet_actif"] = "veille"
            st.rerun()

# ============================================================
# SIDEBAR simple (sans auth)
# ============================================================
def sidebar_simple():
    with st.sidebar:
        st.markdown("## 🔭 Veille IA")
        cfg    = srv.charger_config()
        wp_ok  = bool(cfg.get("wp_base") and cfg.get("wp_user") and cfg.get("wp_password"))
        ftp_ok = srv.ftp_est_configure()
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f'<div style="text-align:center">{"🟢" if wp_ok else "🔴"} <span style="font-size:12px;color:var(--subtext)">WordPress</span></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div style="text-align:center">{"🟢" if ftp_ok else "🔴"} <span style="font-size:12px;color:var(--subtext)">FTP</span></div>', unsafe_allow_html=True)

        st.markdown("---")
        nb_sujets, nb_articles, _ = _compteurs_historique()
        st.markdown(
            f'<div style="display:flex;gap:8px;margin-bottom:16px;">'
            f'<div class="metric-box" style="flex:1"><span class="metric-val">{nb_sujets}</span><span class="metric-lbl">Sujets</span></div>'
            f'<div class="metric-box" style="flex:1"><span class="metric-val">{nb_articles}</span><span class="metric-lbl">Articles</span></div>'
            f'</div>', unsafe_allow_html=True
        )
        st.markdown("## Navigation")
        pages = {
            "🔍 Nouvelle veille": "veille",
            "📚 Historique":      "historique",
            "📊 Comparaison":     "comparaison",
            "⚙️ Configuration":   "config",
        }
        for label, key in pages.items():
            actif = st.session_state["onglet_actif"] == key
            if st.button(label, use_container_width=True,
                         type="primary" if actif else "secondary", key=f"nav2_{key}"):
                st.session_state["onglet_actif"] = key
                st.rerun()
        st.markdown("---")
        st.markdown('<p style="font-size:11px;color:var(--subtext);text-align:center;">Veille auto · Groq · DuckDuckGo</p>', unsafe_allow_html=True)

# ============================================================
# PAGE ABONNEMENT
# ============================================================
def page_abonnement():
    st.markdown("# ✨ Abonnement")
    st.markdown("---")
    abonne = _est_abonne()
    if abonne:
        st.markdown(
            '<div class="card card-green" style="padding:24px;text-align:center;">'
            '<div style="font-size:32px;margin-bottom:8px;">✅</div>'
            '<div style="font-size:18px;font-weight:600;color:var(--green);margin-bottom:8px;">Abonnement actif</div>'
            '<div style="font-size:13px;color:var(--subtext);">Recherches illimitées + veille email quotidienne.</div>'
            '</div>', unsafe_allow_html=True
        )
        st.info("Pour annuler, contactez support@veille-ia.fr")
    else:
        col_l, col_c, col_r = st.columns([1, 1.5, 1])
        with col_c:
            stripe_url = os.getenv("STRIPE_PAYMENT_LINK", "")
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
            used  = quota.get("searches_used", 0)
            reste = max(0, auth.RECHERCHES_GRATUITES - used)
            if reste == 0:
                st.markdown(
                    '<div class="card card-red" style="padding:24px;text-align:center;">'
                    '<div style="font-size:20px;margin-bottom:8px;">🔒</div>'
                    '<div style="font-size:16px;font-weight:600;color:var(--red);margin-bottom:8px;">Limite gratuite atteinte</div>'
                    '<div style="font-size:13px;color:var(--subtext);">Abonnez-vous pour un accès illimité.</div>'
                    '</div>', unsafe_allow_html=True
                )
                if st.button("✨ S'abonner à 2,99€/mois", type="primary"):
                    st.session_state["onglet_actif"] = "abonnement"
                    st.rerun()
                return
            st.markdown(f'<div style="margin-bottom:16px;">{_badge_html(f"Compte gratuit · {reste} recherche(s) restante(s)", "yellow")}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="margin-bottom:16px;">{_badge_html("✨ Abonné · Recherches illimitées", "mauve")}</div>', unsafe_allow_html=True)

    col_form, col_log = st.columns([1, 1], gap="large")

    with col_form:
        st.markdown('<div class="card card-accent">', unsafe_allow_html=True)
        sujet = st.text_area("Sujets de recherche", placeholder="ex: cybersécurité IA, deepfake, LLM Europe", height=90)
        col_a, col_b = st.columns(2)
        with col_a:
            limite = st.number_input("Articles max à résumer", min_value=1, max_value=50, value=10, step=1)
        with col_b:
            mode = st.selectbox("Mode publication", ["Mise à jour page", "Créer un post"])
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            lancer = st.button("▶ Lancer la veille", use_container_width=True,
                               disabled=st.session_state["en_cours"], type="primary")
        with col_btn2:
            if st.button("🗑 Effacer les logs", use_container_width=True):
                st.session_state["logs"] = []
                st.rerun()

        if st.session_state["resultats"]:
            st.markdown("---")
            nb_r = len(st.session_state["resultats"])
            st.markdown(f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;"><span style="font-family:Space Mono;font-size:13px;">Résultats</span>{_badge_html(f"{nb_r} articles", "green")}</div>', unsafe_allow_html=True)
            for r in st.session_state["resultats"][:8]:
                dom   = urlparse(r.get("href","")).netloc
                score = r.get("score", 0)
                couleur = "green" if score >= 80 else "yellow" if score >= 50 else "red"
                st.markdown(
                    f'<div class="card" style="padding:12px 16px;margin-bottom:6px;">'
                    f'<div style="font-size:13px;font-weight:500;margin-bottom:4px;">{r.get("title","")[:72]}…</div>'
                    f'<div style="display:flex;gap:8px;align-items:center;">'
                    f'<span style="font-size:11px;color:var(--subtext)">{dom}</span>'
                    f'{_badge_html(f"score {score}", couleur)}</div></div>', unsafe_allow_html=True
                )
            if nb_r > 8:
                st.caption(f"… et {nb_r - 8} autres articles")

    with col_log:
        st.markdown('<div style="font-family:Space Mono;font-size:12px;color:var(--subtext);text-transform:uppercase;letter-spacing:1px;margin-bottom:10px;">— Journal d\'exécution</div>', unsafe_allow_html=True)
        log_html = "<br>".join(st.session_state["logs"][-40:] if st.session_state["logs"] else ["<span style='color:var(--subtext)'>En attente de lancement…</span>"])
        st.markdown(f'<div class="log-box">{log_html}</div>', unsafe_allow_html=True)
        if st.session_state["en_cours"]:
            st.progress(0.0, text="Traitement en cours…")

    # BUG FIX 2 : lancer peut être non défini si col_form n'est pas encore exécuté.
    # On s'assure qu'il est toujours défini avant usage.
    if lancer and sujet.strip() and not st.session_state["en_cours"]:
        if AUTH_OK and uid:
            ok_q, msg_q = auth.peut_rechercher(uid)
            if not ok_q:
                st.error(msg_q)
                return

        st.session_state["en_cours"]      = True
        st.session_state["resultats"]     = []
        st.session_state["sujet_courant"] = sujet.strip()
        st.session_state["logs"]          = []
        _log(f"Démarrage — sujet : {sujet.strip()}")

        try:
            resultats = srv.rechercher(sujet.strip(), callback_statut=_log)
            st.session_state["resultats"] = resultats
            _log(f"{len(resultats)} résultats — lancement du workflow IA")

            if AUTH_OK and uid and not abonne:
                auth.incrementer_quota(uid)

            if mode == "Mise à jour page":
                resultats_pub = srv.workflow_publier(sujet.strip(), resultats, callback_statut=_log, limite=int(limite))
                for canal, (ok, msg) in resultats_pub.items():
                    _log(f"{'OK' if ok else 'ERREUR'} {canal.upper()} : {msg}")
            else:
                ok, msg = srv.workflow_creer_post(sujet.strip(), resultats[:int(limite)], callback_statut=_log)
                _log(f"{'OK' if ok else 'ERREUR'} Post : {msg}")
        except Exception as e:
            _log(f"Erreur : {e}")

        st.session_state["en_cours"] = False
        st.rerun()

    elif lancer and not sujet.strip():
        st.warning("Entrez au moins un sujet de recherche.")

# ============================================================
# PAGE HISTORIQUE
# ============================================================
def page_historique():
    st.markdown("# 📚 Historique des veilles")
    st.markdown("---")
    h = srv.charger_historique()
    sujets = [k for k in h if not k.startswith("__") and isinstance(h[k], list)]
    if not sujets:
        st.info("Aucun historique. Lancez une première veille.")
        return
    col_gauche, col_droite = st.columns([1, 2], gap="large")
    with col_gauche:
        sujet_sel = st.selectbox("Sujet", sujets)
        sessions  = h.get(sujet_sel, [])
        st.markdown(f'<div class="metric-box" style="margin:12px 0;"><span class="metric-val">{len(sessions)}</span><span class="metric-lbl">Sessions</span></div>', unsafe_allow_html=True)
        if st.button("🗑 Effacer tout l'historique", type="secondary", use_container_width=True):
            srv.effacer_historique()
            st.success("Historique effacé.")
            st.rerun()
    with col_droite:
        for i, session in enumerate(sessions):
            if not isinstance(session, dict):
                continue
            date_s   = session.get("date", "?")
            articles = session.get("articles", [])
            rg       = session.get("resume_global", "")
            with st.expander(f"📅 {date_s} — {len(articles)} articles", expanded=(i == 0)):
                if rg and not rg.startswith("Erreur"):
                    st.markdown(
                        f'<div class="card" style="border-left:3px solid var(--yellow);margin-bottom:16px;">'
                        f'<div style="font-size:12px;font-weight:600;color:var(--yellow);margin-bottom:8px;">SYNTHÈSE</div>'
                        f'<div style="font-size:13px;line-height:1.7;">{rg[:1200]}…</div></div>',
                        unsafe_allow_html=True
                    )
                for a in sorted(articles, key=lambda x: x.get("score", 0), reverse=True):
                    dom    = urlparse(a.get("href","")).netloc
                    score  = a.get("score", 0)
                    points = a.get("resume_ollama", [])
                    doublon = a.get("doublon_de","")
                    pts_html = ""
                    if points and points != ["Contenu non accessible pour ce site."]:
                        pts_html = "".join(f'<li style="font-size:12px;color:var(--subtext);margin:3px 0;line-height:1.6">{p}</li>' for p in points[:3])
                        pts_html = f"<ul style='padding-left:18px;margin:6px 0 0 0'>{pts_html}</ul>"
                    badge_d = '<span class="badge badge-yellow" style="margin-left:8px">~doublon</span>' if doublon else ""
                    st.markdown(
                        f'<div class="card" style="padding:12px 16px;margin-bottom:6px;">'
                        f'<div style="display:flex;justify-content:space-between;align-items:flex-start;">'
                        f'<div style="font-size:13px;font-weight:500;flex:1"><a href="{a.get("href","")}" target="_blank" style="color:var(--blue);text-decoration:none">{a.get("title","")[:80]}</a>{badge_d}</div>'
                        f'<span class="badge badge-blue" style="margin-left:12px;white-space:nowrap">{score}</span></div>'
                        f'<div style="font-size:11px;color:var(--subtext);margin-top:4px">{dom}</div>'
                        f'{pts_html}</div>', unsafe_allow_html=True
                    )

# ============================================================
# PAGE COMPARAISON
# ============================================================
def page_comparaison():
    st.markdown("# 📊 Comparaison de sessions")
    st.markdown("### Identifiez les évolutions entre deux veilles")
    st.markdown("---")
    h = srv.charger_historique()
    sujets = [k for k in h if not k.startswith("__") and isinstance(h[k], list)]
    if not sujets:
        st.info("Aucun historique disponible.")
        return
    sujet_sel = st.selectbox("Sujet à comparer", sujets)
    sessions  = [s for s in h.get(sujet_sel, []) if isinstance(s, dict)]
    if len(sessions) < 2:
        st.warning("Il faut au moins 2 sessions pour comparer.")
        return
    dates = [s.get("date", f"Session {i+1}") for i, s in enumerate(sessions)]
    col1, col2 = st.columns(2)
    with col1:
        date_rec = st.selectbox("Session récente", dates, index=0)
    with col2:
        # BUG FIX 3 : index=1 pouvait crasher si len(dates)==1, déjà protégé
        # mais on sécurise mieux avec min()
        date_anc = st.selectbox("Session précédente", dates, index=min(1, len(dates) - 1))
    if date_rec == date_anc:
        st.warning("Choisissez deux sessions différentes.")
        return
    sess_rec = next((s for s in sessions if s.get("date") == date_rec), None)
    sess_anc = next((s for s in sessions if s.get("date") == date_anc), None)
    if not sess_rec or not sess_anc:
        st.error("Sessions introuvables.")
        return
    hrefs_anc = {a["href"] for a in sess_anc.get("articles", []) if "href" in a}  # BUG FIX 4 : KeyError si "href" absent
    hrefs_rec = {a["href"] for a in sess_rec.get("articles", []) if "href" in a}  # BUG FIX 4 : idem
    nouveaux  = hrefs_rec - hrefs_anc
    disparus  = hrefs_anc - hrefs_rec
    col_stat1, col_stat2, col_stat3 = st.columns(3)
    for col, val, lbl, clr in [
        (col_stat1, len(sess_rec.get("articles",[])), "Articles récents", "blue"),
        (col_stat2, len(nouveaux), "Nouveaux", "green"),
        (col_stat3, len(disparus), "Disparus", "red"),
    ]:
        with col:
            st.markdown(f'<div class="metric-box"><span class="metric-val" style="color:var(--{clr})">{val}</span><span class="metric-lbl">{lbl}</span></div>', unsafe_allow_html=True)
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    if st.button("🧠 Générer l'analyse comparative", type="primary"):
        with st.spinner("Analyse IA en cours…"):
            try:
                analyse = srv.comparer_sessions(sujet_sel, sess_rec, sess_anc)
                st.markdown(
                    f'<div class="card card-accent" style="margin-top:16px;">'
                    f'<div style="font-size:12px;font-weight:600;color:var(--mauve);margin-bottom:12px;">ANALYSE COMPARATIVE — {sujet_sel.upper()}</div>'
                    f'<div style="font-size:13px;line-height:1.8;white-space:pre-line">{analyse}</div></div>',
                    unsafe_allow_html=True
                )
            except Exception as e:
                st.error(f"Erreur : {e}")
    if nouveaux:
        st.markdown("#### ✨ Nouveaux articles")
        arts_rec = {a["href"]: a for a in sess_rec.get("articles", []) if "href" in a}  # BUG FIX 4 : cohérence
        for href in list(nouveaux)[:6]:
            a   = arts_rec.get(href, {})
            dom = urlparse(href).netloc
            st.markdown(
                f'<div class="card" style="padding:10px 14px;margin-bottom:6px;">'
                f'<a href="{href}" target="_blank" style="color:var(--green);font-size:13px;font-weight:500">{a.get("title", href[:60])}</a>'
                f'<div style="font-size:11px;color:var(--subtext);margin-top:2px">{dom}</div></div>',
                unsafe_allow_html=True
            )
    if disparus:
        with st.expander(f"🗃 Articles disparus ({len(disparus)})"):
            arts_anc = {a["href"]: a for a in sess_anc.get("articles", []) if "href" in a}  # BUG FIX 4 : cohérence
            for href in list(disparus)[:6]:
                a = arts_anc.get(href, {})
                st.markdown(f'<div style="font-size:12px;color:var(--subtext);padding:6px 0;border-bottom:1px solid var(--border)">{a.get("title", href[:60])}</div>', unsafe_allow_html=True)

# ============================================================
# PAGE CONFIGURATION
# ============================================================
def page_config():
    st.markdown("# ⚙️ Configuration")
    st.markdown("---")
    cfg = srv.charger_config()
    tab_wp, tab_ftp = st.tabs(["🌐 WordPress", "📡 FTP"])

    with tab_wp:
        st.markdown("#### Connexion WordPress (API REST)")
        wp_base = st.text_input("URL du site", value=cfg.get("wp_base", ""), placeholder="https://monsite.com")
        col1, col2 = st.columns(2)
        with col1:
            wp_user = st.text_input("Identifiant", value=cfg.get("wp_user", ""))
        with col2:
            wp_pwd = st.text_input("Mot de passe d'application", value=cfg.get("wp_password", ""), type="password")

        col_save, col_test = st.columns(2)
        with col_save:
            if st.button("💾 Sauvegarder WP", use_container_width=True):
                cfg.update({"wp_base": wp_base, "wp_user": wp_user, "wp_password": wp_pwd})
                srv.sauvegarder_config(cfg)
                st.success("Configuration WordPress sauvegardée !")
        with col_test:
            if st.button("🔌 Tester la connexion WP", use_container_width=True):
                ok, msg = srv.tester_connexion_wp(wp_base, wp_user, wp_pwd)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)

        st.markdown(
            '<div class="card" style="margin-top:12px;">'
            '<div style="font-size:12px;color:var(--subtext);line-height:1.8;">'
            '<strong style="color:var(--text)">Créer un mot de passe d\'application :</strong><br>'
            '1. WordPress → Profil → Mots de passe d\'application<br>'
            '2. Donnez un nom et cliquez « Ajouter »<br>'
            '3. Copiez le mot de passe généré ici'
            '</div></div>', unsafe_allow_html=True
        )

    with tab_ftp:
        st.markdown("#### Connexion FTP (publication directe)")
        ftp_host = st.text_input("Hôte FTP", value=cfg.get("ftp_host", ""), placeholder="ftp.monhebergeur.com")
        col1, col2 = st.columns(2)
        with col1:
            ftp_user = st.text_input("Utilisateur FTP", value=cfg.get("ftp_user", ""))
        with col2:
            ftp_pwd = st.text_input("Mot de passe FTP", value=cfg.get("ftp_password", ""), type="password")
        ftp_path = st.text_input("Chemin distant", value=cfg.get("ftp_path", "/htdocs/veille-ia.html"))

        col_save, col_test = st.columns(2)
        with col_save:
            if st.button("💾 Sauvegarder FTP", use_container_width=True):
                cfg.update({"ftp_host": ftp_host, "ftp_user": ftp_user,
                            "ftp_password": ftp_pwd, "ftp_path": ftp_path})
                srv.sauvegarder_config(cfg)
                st.success("Configuration FTP sauvegardée !")
        with col_test:
            if st.button("🔌 Tester FTP", use_container_width=True):
                ok, msg = srv.tester_connexion_ftp(ftp_host, ftp_user, ftp_pwd)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)

    st.markdown("---")
    st.markdown("#### Informations système")
    col1, col2, col3 = st.columns(3)
    racine  = os.environ.get("VEILLE_RACINE", os.path.dirname(os.path.abspath(__file__)))
    app_dir = os.path.join(racine, ".app")
    with col1:
        st.markdown(f'<div class="card"><div style="font-size:11px;color:var(--subtext)">Dossier données</div><div style="font-size:12px;font-family:Space Mono;margin-top:4px;word-break:break-all">{app_dir}</div></div>', unsafe_allow_html=True)
    with col2:
        try:
            import ddgs
            ddgs_ok = "✅ ddgs"
        except ImportError:
            ddgs_ok = "❌ ddgs manquant"
        try:
            import feedparser
            fp_ok = "✅ feedparser"
        except ImportError:
            fp_ok = "❌ feedparser manquant"
        st.markdown(f'<div class="card"><div style="font-size:12px;margin-bottom:4px">{ddgs_ok}</div><div style="font-size:12px">{fp_ok}</div></div>', unsafe_allow_html=True)
    with col3:
        nb_s, nb_a, _ = _compteurs_historique()
        st.markdown(f'<div class="card"><div style="font-size:12px;color:var(--subtext)">Historique</div><div style="font-size:12px;margin-top:4px">{nb_s} sujets · {nb_a} articles</div></div>', unsafe_allow_html=True)

# ============================================================
# ROUTING PRINCIPAL
# ============================================================
user = st.session_state.get("user")

if AUTH_OK and not user:
    page_auth()
else:
    if AUTH_OK and user:
        sidebar_connecte()
    else:
        sidebar_simple()

    page = st.session_state["onglet_actif"]
    if page == "veille":
        page_veille()
    elif page == "historique":
        page_historique()
    elif page == "comparaison":
        page_comparaison()
    elif page == "config":
        page_config()
    elif page == "abonnement":
        page_abonnement()
    else:
        page_veille()