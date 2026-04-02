# ============================================================
# APP.PY — Veille IA
# ============================================================

import streamlit as st
import os
import json
import time
from datetime import datetime
from urllib.parse import urlparse

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception as e:
    print(f"[app] dotenv indisponible: {e}")

import serveur as srv
import security

AUTH_OK = False
try:
    import auth
    AUTH_OK = True
except Exception as e:
    print(f"[app] module auth indisponible: {e}")

STORAGE_OK = False
try:
    import storage
    STORAGE_OK = True
except Exception as e:
    print(f"[app] module storage indisponible: {e}")

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
.stTextInput>div>div>input,.stTextArea textarea,.stNumberInput input{background:var(--overlay)!important;border:1px solid var(--border)!important;color:var(--text)!important;border-radius:8px!important;}
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
.code-block{background:#0d0d1a;border:1px solid var(--border);border-radius:8px;padding:14px 16px;font-family:'Space Mono',monospace;font-size:12px;color:#a6e3a1;line-height:1.7;overflow-x:auto;white-space:pre;}
hr{border-color:var(--border)!important;margin:16px 0!important;}
#MainMenu,footer,.stDeployButton{display:none!important;}
::-webkit-scrollbar{width:6px;}
::-webkit-scrollbar-track{background:var(--surface);}
::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px;}
.stSelectbox div[data-baseweb="select"]>div{background:var(--overlay)!important;border-color:var(--border)!important;color:var(--text)!important;border-radius:8px!important;}
.stNumberInput [data-baseweb="input"]{background:var(--overlay)!important;border-color:var(--border)!important;}
.streamlit-expanderHeader{background:var(--surface)!important;border-radius:8px!important;color:var(--text)!important;}
@keyframes pulse-ring{0%{transform:scale(.8);opacity:1}100%{transform:scale(2.2);opacity:0}}
@keyframes scan-line{0%{transform:translateY(-100%)}100%{transform:translateY(400%)}}
@keyframes counter-up{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
@keyframes dot-blink{0%,80%,100%{opacity:0}40%{opacity:1}}
.launch-overlay{background:linear-gradient(135deg,#0d0d1a 0%,#1e1e2e 100%);border:1px solid var(--blue);border-radius:16px;padding:40px 32px;text-align:center;position:relative;overflow:hidden;margin-bottom:16px;}
.launch-icon-wrap{position:relative;display:inline-block;width:80px;height:80px;margin-bottom:20px;}
.launch-icon{font-size:48px;line-height:80px;position:relative;z-index:2;display:block;}
.pulse-ring{position:absolute;top:50%;left:50%;width:60px;height:60px;margin:-30px 0 0 -30px;border:2px solid var(--blue);border-radius:50%;animation:pulse-ring 1.4s ease-out infinite;z-index:1;}
.pulse-ring:nth-child(2){animation-delay:.4s}.pulse-ring:nth-child(3){animation-delay:.8s}
.scan-line{position:absolute;left:0;right:0;height:2px;background:linear-gradient(90deg,transparent,var(--blue),transparent);animation:scan-line 2s linear infinite;opacity:.6;}
.launch-title{font-family:'Space Mono',monospace;font-size:18px;color:var(--blue);margin-bottom:8px;letter-spacing:1px;}
.launch-subject{font-size:13px;color:var(--subtext);margin-bottom:24px;font-style:italic;}
.launch-steps{display:flex;justify-content:center;gap:24px;margin-bottom:20px;flex-wrap:wrap;}
.launch-step{display:flex;flex-direction:column;align-items:center;gap:6px;animation:counter-up .4s ease forwards;opacity:0;}
.launch-step:nth-child(1){animation-delay:.1s}.launch-step:nth-child(2){animation-delay:.3s}.launch-step:nth-child(3){animation-delay:.5s}.launch-step:nth-child(4){animation-delay:.7s}
.step-icon{font-size:22px}.step-label{font-size:11px;color:var(--subtext);text-transform:uppercase;letter-spacing:1px;}
.typing-dots span{display:inline-block;width:6px;height:6px;background:var(--blue);border-radius:50%;margin:0 2px;animation:dot-blink 1.2s infinite;}
.typing-dots span:nth-child(2){animation-delay:.2s}.typing-dots span:nth-child(3){animation-delay:.4s}
.launch-status{font-family:'Space Mono',monospace;font-size:12px;color:var(--green);margin-top:8px;min-height:20px;}
.pub-panel{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:20px;margin-top:20px;}
</style>
""", unsafe_allow_html=True)

# ============================================================
# THÈME PAR DÉFAUT
# ============================================================
THEME_DEFAULT = {
    "bg":"#1e1e2e","surf":"#181825","ov":"#313244",
    "txt":"#cdd6f4","sub":"#a6adc8","brd":"#45475a",
    "blue":"#89b4fa","grn":"#a6e3a1","yel":"#f9e2af","red":"#f38ba8",
    "font":"Arial,sans-serif","fs":"13","rad":"8",
    "ptitle":"Veille Technologique IA","stitle":"Intelligence Artificielle",
}

# ============================================================
# SESSION STATE
# ============================================================
def _init_state():
    defaults = {
        "resultats":[],"sujet_courant":"","logs":[],
        "en_cours":False,"en_cours_pub":False,"page":"accueil",
        "user":None,"session":None,"profil":{},
        "dernier_log":"",
        "theme_widget_version": 0,
        "theme_ftp": dict(THEME_DEFAULT),
        "recherche_terminee": False,
        "limite_courante": 10,
        "derniere_publication": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()

# Restaure la session utilisateur si possible (evite les deconnexions
# frequentes lorsque la session Streamlit est recreee).
if AUTH_OK and not st.session_state.get("user"):
    try:
        res_sess = auth.recuperer_session()
        if not res_sess.get("ok"):
            res_sess = auth.rafraichir_session()
        if res_sess.get("ok"):
            st.session_state["user"] = res_sess.get("user")
            st.session_state["session"] = res_sess.get("session")
            try:
                st.session_state["profil"] = auth.get_profil(res_sess["user"].id)
            except Exception:
                st.session_state["profil"] = {}
    except Exception:
        pass

# ============================================================
# HELPERS
# ============================================================
def _log(msg):
    h = datetime.now().strftime("%H:%M:%S")
    st.session_state["logs"].append(f"[{h}] {msg}")
    st.session_state["dernier_log"] = msg
    if len(st.session_state["logs"]) > 120:
        st.session_state["logs"] = st.session_state["logs"][-100:]

def _badge(label, style="blue"):
    return f'<span class="badge badge-{style}">{label}</span>'

def _user_id():
    u = st.session_state.get("user")
    return u.id if u else None

def _est_abonne():
    if not AUTH_OK:
        return False
    uid = _user_id()
    return auth.est_abonne(uid) if uid else False

def _conditions_acceptees():
    if not AUTH_OK:
        return True
    uid = _user_id()
    if not uid:
        return False
    profil = st.session_state.get("profil") or {}
    if "terms_accepted" in profil:
        return bool(profil.get("terms_accepted"))
    try:
        profil = auth.get_profil(uid) or {}
        st.session_state["profil"] = profil
        return bool(profil.get("terms_accepted"))
    except Exception:
        return False

def _goto(page):
    st.session_state["page"] = page
    st.rerun()

def _cfg():
    if STORAGE_OK:
        try:
            return storage.charger_config()
        except Exception as e:
            print(f"[app] fallback config locale (storage): {e}")
    return srv.charger_config()

def _save_cfg(c):
    if STORAGE_OK:
        try:
            storage.sauvegarder_config(c)
            return
        except Exception as e:
            print(f"[app] fallback sauvegarde config locale: {e}")
    srv.sauvegarder_config(c)

def _historique():
    if STORAGE_OK:
        try:
            return storage.charger_historique()
        except Exception as e:
            print(f"[app] fallback historique local: {e}")
    return srv.charger_historique()

def _effacer_sujet(sujet):
    h = _historique()
    if sujet in h:
        del h[sujet]
        if STORAGE_OK:
            try:
                storage.sauvegarder_historique(h)
                return
            except Exception:
                pass
        srv.sauvegarder_historique(h)

def _effacer_tout():
    if STORAGE_OK:
        try:
            storage.effacer_historique()
            return
        except Exception:
            pass
    srv.effacer_historique()

def _activer_storage(user_id):
    if STORAGE_OK and user_id:
        try:
            storage.set_user(user_id)
            srv.set_storage_context(storage)
        except Exception:
            pass

def _appliquer_theme(valeurs: dict):
    st.session_state["theme_ftp"].update(valeurs)
    st.session_state["theme_widget_version"] += 1

# ============================================================
# SIDEBAR
# ============================================================
def render_sidebar():
    user   = st.session_state.get("user")
    page   = st.session_state["page"]
    abonne = _est_abonne()

    with st.sidebar:
        st.markdown("## 🔭 Veille IA")
        st.markdown("---")

        if user:
            email = user.email if user else "?"
            st.markdown(
                f'<div style="padding:12px;background:var(--overlay);border-radius:10px;margin-bottom:12px;">'
                f'<div style="font-size:11px;color:var(--subtext);margin-bottom:3px;">Connecté</div>'
                f'<div style="font-size:12px;font-weight:500;word-break:break-all;">{email}</div>'
                f'<div style="margin-top:6px;">'
                f'{"<span class=\'badge badge-mauve\'>✨ Abonné</span>" if abonne else "<span class=\'badge badge-yellow\'>Gratuit</span>"}'
                f'</div></div>', unsafe_allow_html=True)
            if not abonne:
                st.markdown(
                    '<div style="background:rgba(203,166,247,.08);border:1px solid var(--mauve);'
                    'border-radius:10px;padding:10px;margin-bottom:12px;text-align:center;">'
                    '<div style="font-size:11px;color:var(--mauve);font-weight:600;margin-bottom:3px;">Passer à illimité</div>'
                    '<div style="font-size:20px;font-weight:700;">2,99€'
                    '<span style="font-size:11px;font-weight:400;color:var(--subtext)">/mois</span></div>'
                    '</div>', unsafe_allow_html=True)
            st.markdown("---")
            st.markdown("## Navigation")
            pages = {
                "🔍 Nouvelle veille": "veille",
                "📚 Historique":      "historique",
                "📊 Comparaison":     "comparaison",
                "⏰ Automatisation":  "auto",
                "⚙️ Configuration":   "config",
                "✨ Abonnement":      "abonnement",
                "📄 Conditions":      "conditions",
                "🛡️ Conformité RGPD": "conformite",
            }
            for label, key in pages.items():
                actif = page == key
                if st.button(label, use_container_width=True,
                             type="primary" if actif else "secondary", key=f"sb_nav_{key}"):
                    st.session_state["page"] = key
                    st.rerun()
            st.markdown("---")
            if st.button("🚪 Déconnexion", use_container_width=True, key="sb_logout"):
                if AUTH_OK:
                    try:
                        auth.deconnecter()
                    except Exception:
                        pass
                if STORAGE_OK:
                    try:
                        storage.set_user(None)
                    except Exception:
                        pass
                st.session_state.update({
                    "user": None, "session": None, "profil": {},
                    "page": "accueil", "dernier_log": "",
                    "recherche_terminee": False, "derniere_publication": None,
                })
                st.rerun()
        else:
            st.markdown(
                '<div style="font-size:12px;color:var(--subtext);text-align:center;margin-bottom:12px;">'
                'Connectez-vous pour accéder à la plateforme</div>', unsafe_allow_html=True)
            if st.button("🔑 Se connecter / S'inscrire", use_container_width=True,
                         type="primary", key="sb_login"):
                st.session_state["page"] = "accueil"
                st.rerun()
            st.markdown("---")
            st.markdown(
                '<p style="font-size:11px;color:var(--subtext);text-align:center;">'
                'Veille auto · Groq · DuckDuckGo</p>', unsafe_allow_html=True)

# ============================================================
# PAGE ACCUEIL / AUTH
# ============================================================
def page_accueil():
    if not AUTH_OK:
        st.error("Service d'authentification indisponible.")
        return

    col_l, col_c, col_r = st.columns([1, 1.2, 1])
    with col_c:
        st.markdown("<div style='height:30px'></div>", unsafe_allow_html=True)
        st.markdown(
            '<div style="text-align:center;margin-bottom:32px;">'
            '<div style="font-family:Space Mono;font-size:28px;color:var(--blue);">🔭 Veille IA</div>'
            '<div style="font-size:14px;color:var(--subtext);margin-top:10px;">'
            'Plateforme de veille académique automatisée</div>'
            '</div>', unsafe_allow_html=True)

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
                        st.session_state["page"]    = "veille"
                        _activer_storage(res["user"].id)
                        st.rerun()
                    else:
                        st.error(res["message"])

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            if st.button("Mot de passe oublié ?", use_container_width=True, key="btn_reset_pwd"):
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
                '</div></div>', unsafe_allow_html=True)
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
# ÉDITEUR DE THÈME FTP
# ============================================================
def _render_theme_editor():
    th  = st.session_state["theme_ftp"]
    ver = st.session_state["theme_widget_version"]

    st.markdown("---")
    st.markdown(
        '<div style="font-family:Space Mono;font-size:13px;color:var(--blue);">'
        '🎨 Personnaliser le thème de veille-ia.html</div>', unsafe_allow_html=True)
    st.markdown(
        '<div style="font-size:12px;color:var(--subtext);margin:6px 0 16px 0;">'
        'Modifiez l\'apparence de la page publiée sur votre hébergement FTP.</div>',
        unsafe_allow_html=True)

    PRESETS = {
        "🌙 Catppuccin": {"bg":"#1e1e2e","surf":"#181825","ov":"#313244","txt":"#cdd6f4","sub":"#a6adc8","brd":"#45475a","blue":"#89b4fa","grn":"#a6e3a1","yel":"#f9e2af","red":"#f38ba8"},
        "☀️ Light":      {"bg":"#f8f9fa","surf":"#ffffff","ov":"#e9ecef","txt":"#212529","sub":"#6c757d","brd":"#dee2e6","blue":"#0d6efd","grn":"#198754","yel":"#e67e00","red":"#dc3545"},
        "❄️ Nord":       {"bg":"#2e3440","surf":"#3b4252","ov":"#434c5e","txt":"#eceff4","sub":"#d8dee9","brd":"#4c566a","blue":"#88c0d0","grn":"#a3be8c","yel":"#ebcb8b","red":"#bf616a"},
        "🧛 Dracula":    {"bg":"#282a36","surf":"#1e1f29","ov":"#44475a","txt":"#f8f8f2","sub":"#6272a4","brd":"#44475a","blue":"#8be9fd","grn":"#50fa7b","yel":"#f1fa8c","red":"#ff5555"},
    }

    cols = st.columns(len(PRESETS) + 1)
    for i, (label, vals) in enumerate(PRESETS.items()):
        with cols[i]:
            if st.button(label, use_container_width=True, key=f"preset_{i}"):
                _appliquer_theme(vals)
                st.rerun()
    with cols[len(PRESETS)]:
        if st.button("🔄 Reset", use_container_width=True, key="btn_reset_theme"):
            _appliquer_theme(dict(THEME_DEFAULT))
            try:
                cfg = _cfg()
                cfg.pop("theme_ftp", None)
                _save_cfg(cfg)
            except Exception:
                pass
            st.rerun()

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("**Couleurs**")
        sub_cols = st.columns(2)
        color_fields = [
            ("bg","Fond page"),("surf","Fond carte"),("ov","Fond hover"),("txt","Texte"),
            ("sub","Sous-texte"),("brd","Bordure"),("blue","Bleu (liens)"),("grn","Vert"),
            ("yel","Jaune (synthèse)"),("red","Rouge"),
        ]
        for i, (key, label) in enumerate(color_fields):
            with sub_cols[i % 2]:
                val = st.color_picker(label, value=th.get(key, "#ffffff"), key=f"th_{key}_v{ver}")
                st.session_state["theme_ftp"][key] = val

    with col_right:
        st.markdown("**Typographie & Mise en page**")
        font_opts = ["Arial,sans-serif","'Segoe UI',sans-serif","Georgia,serif","'Courier New',monospace","'Inter',sans-serif"]
        cur_font  = th.get("font", "Arial,sans-serif")
        font_idx  = font_opts.index(cur_font) if cur_font in font_opts else 0
        font = st.selectbox("Police", font_opts, index=font_idx, key=f"th_font_v{ver}")
        st.session_state["theme_ftp"]["font"] = font

        fs  = st.slider("Taille du texte (px)", 11, 16, int(th.get("fs", 13)), key=f"th_fs_v{ver}")
        st.session_state["theme_ftp"]["fs"] = str(fs)

        rad = st.slider("Rayon des cartes (px)", 0, 20, int(th.get("rad", 8)), key=f"th_rad_v{ver}")
        st.session_state["theme_ftp"]["rad"] = str(rad)

        st.markdown("**Textes**")
        ptitle = st.text_input("Titre de la page", value=th.get("ptitle", "Veille Technologique IA"), key=f"th_ptitle_v{ver}")
        st.session_state["theme_ftp"]["ptitle"] = ptitle

    t = st.session_state["theme_ftp"]
    st.markdown(
        f'<div style="margin-top:12px;padding:16px;background:{t["bg"]};border-radius:{t["rad"]}px;'
        f'border:1px solid {t["brd"]};font-family:{t["font"]};">'
        f'<div style="font-size:18px;font-weight:bold;color:{t["blue"]};margin-bottom:10px;">{t["ptitle"]}</div>'
        f'<div style="font-size:12px;color:{t["sub"]};margin-bottom:12px;">Aperçu — {datetime.now().strftime("%d/%m/%Y")}</div>'
        f'<div style="background:{t["ov"]};border-radius:{t["rad"]}px;padding:10px 14px;margin-bottom:8px;">'
        f'<div style="font-size:13px;font-weight:600;color:{t["blue"]};">Article exemple</div>'
        f'<div style="font-size:12px;color:{t["sub"]};margin-top:4px;">Les LLM open-source rivalisent avec GPT-4 sur les benchmarks</div>'
        f'</div>'
        f'<div style="padding:12px;background:linear-gradient(135deg,{t["bg"]},{t["surf"]});'
        f'border-left:4px solid {t["yel"]};border-radius:{t["rad"]}px;">'
        f'<div style="font-size:12px;font-weight:bold;color:{t["yel"]};margin-bottom:6px;">— Synthèse</div>'
        f'<div style="font-size:11px;color:{t["txt"]};border-left:2px solid {t["brd"]};padding-left:8px;">'
        f'La convergence des modèles open-source s\'accélère [1]</div>'
        f'</div></div>',
        unsafe_allow_html=True)

    col_apply, col_save = st.columns(2)
    with col_apply:
        if st.button("🎨 Appliquer & republier sur FTP", type="primary",
                     use_container_width=True, key="btn_apply_theme"):
            if srv.ftp_est_configure():
                with st.spinner("Regénération et upload FTP…"):
                    try:
                        h = _historique()
                        ok, msg = srv._publier_ftp_avec_historique(None, h, st.session_state["theme_ftp"])
                        if ok:
                            st.success(f"✅ {msg}")
                        else:
                            st.error(msg)
                    except Exception as e:
                        st.error(f"Erreur : {e}")
            else:
                st.warning("FTP non configuré — allez dans Configuration.")
    with col_save:
        if st.button("💾 Sauvegarder le thème", use_container_width=True, key="btn_save_theme"):
            cfg = _cfg()
            cfg["theme_ftp"] = json.dumps(st.session_state["theme_ftp"])
            _save_cfg(cfg)
            st.success("Thème sauvegardé !")

# ============================================================
# PAGE AUTOMATISATION
# ============================================================
def page_auto():
    st.markdown("# ⏰ Veille automatique")
    st.markdown("### Recevez votre veille par email chaque jour à l'heure de votre choix")
    st.markdown("---")
    if not _est_abonne():
        st.markdown(
            '<div class="card card-mauve" style="padding:24px;text-align:center;">'
            '<div style="font-size:20px;margin-bottom:8px;">🔒</div>'
            '<div style="font-size:16px;font-weight:600;color:var(--mauve);margin-bottom:8px;">Fonctionnalité Premium</div>'
            '<div style="font-size:13px;color:var(--subtext);">La veille automatique par email est réservée aux abonnés.</div>'
            '</div>', unsafe_allow_html=True)
        if st.button("✨ S'abonner à 2,99€/mois", type="primary"):
            _goto("abonnement")
        return
    uid   = _user_id()
    prefs = {}
    if STORAGE_OK:
        try:
            prefs = storage.charger_veille_auto(uid) or {}
        except Exception:
            prefs = {}
    st.markdown('<div class="card card-accent">', unsafe_allow_html=True)
    st.markdown("#### Configurer votre veille automatique")
    sujets = st.text_area("Sujets (séparés par des virgules)", value=prefs.get("sujets", ""),
                           placeholder="ex: intelligence artificielle, cybersécurité, LLM", height=80)
    st.markdown("#### Heure d'envoi")
    st.markdown('<div style="font-size:12px;color:var(--subtext);margin-bottom:12px;">La Réunion = UTC+4 · France = UTC+1 (hiver) / UTC+2 (été)</div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        heure_utc = st.selectbox("Heure (UTC)", list(range(24)), index=int(prefs.get("heure", 4)),
                                  format_func=lambda h: f"{h:02d}h")
    with col2:
        opts    = [0, 15, 30, 45]
        min_val = int(prefs.get("minute", 0))
        min_idx = opts.index(min_val) if min_val in opts else 0
        minute_utc = st.selectbox("Minute", opts, index=min_idx, format_func=lambda m: f"{m:02d}")
    with col3:
        h_reunion = (heure_utc + 4) % 24
        st.markdown(
            f'<div class="metric-box" style="margin-top:20px;">'
            f'<span class="metric-val" style="font-size:20px;">{h_reunion:02d}h{minute_utc:02d}</span>'
            f'<span class="metric-lbl">Heure Réunion (UTC+4)</span></div>', unsafe_allow_html=True)
    actif = st.toggle("Activer la veille automatique", value=bool(prefs.get("actif", True)))
    st.markdown("</div>", unsafe_allow_html=True)
    if prefs.get("derniere_execution"):
        try:
            d = datetime.fromisoformat(str(prefs["derniere_execution"]).replace("Z", "+00:00"))
            st.markdown(f'<div style="font-size:12px;color:var(--subtext);margin-top:8px;">Dernière exécution : {d.strftime("%d/%m/%Y à %H:%M")} UTC</div>', unsafe_allow_html=True)
        except Exception:
            pass
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    if st.button("💾 Enregistrer", type="primary"):
        ok_sujets, msg_sujets = security.valider_texte_recherche(sujets, longueur_max=500)
        if not ok_sujets:
            st.error(msg_sujets)
        elif not STORAGE_OK:
            st.error("Module storage indisponible.")
        else:
            try:
                ok = storage.sauvegarder_veille_auto(sujets.strip(), int(heure_utc), int(minute_utc), actif, uid)
                if ok:
                    st.success(f"Veille {'activée' if actif else 'désactivée'} — envoi à {h_reunion:02d}h{minute_utc:02d} (Réunion)")
                else:
                    st.error("Erreur Supabase.")
            except Exception as e:
                st.error(f"Erreur : {e}")
    st.markdown("---")
    st.markdown(
        '<div class="card" style="padding:16px;">'
        '<div style="font-size:13px;font-weight:600;margin-bottom:8px;">Comment ça fonctionne</div>'
        '<div style="font-size:12px;color:var(--subtext);line-height:1.9;">'
        '1. Un robot tourne automatiquement sur nos serveurs toutes les heures<br>'
        '2. À l\'heure choisie, il lance la recherche sur vos sujets<br>'
        '3. Il génère les résumés IA et vous envoie un email<br>'
        '4. Vous n\'avez rien à faire — tout se passe sans connexion'
        '</div></div>', unsafe_allow_html=True)

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
            '</div>', unsafe_allow_html=True)
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
                '</div></div>', unsafe_allow_html=True)
            if stripe_url:
                st.markdown(
                    f'<a href="{stripe_url}" target="_blank" style="display:block;text-align:center;'
                    f'background:var(--mauve);color:#1e1e2e;font-weight:700;font-size:15px;'
                    f'padding:14px;border-radius:10px;text-decoration:none;">'
                    f'✨ S\'abonner — 2,99€/mois</a>', unsafe_allow_html=True)
            else:
                st.warning("Paiement Stripe disponible prochainement.")

# ============================================================
# PAGE VEILLE
# ============================================================
def page_veille():
    st.markdown("# 🔍 Nouvelle veille")
    st.markdown("### Recherche, scoring et publication")
    st.markdown("---")

    uid    = _user_id()
    abonne = _est_abonne()

    if AUTH_OK and uid:
        if not abonne:
            quota = auth.get_quota(uid)
            reste = max(0, auth.RECHERCHES_GRATUITES - quota.get("searches_used", 0))
            if reste == 0:
                st.markdown(
                    '<div class="card card-red" style="padding:24px;text-align:center;">'
                    '<div style="font-size:20px;margin-bottom:8px;">🔒</div>'
                    '<div style="font-size:16px;font-weight:600;color:var(--red);margin-bottom:8px;">Limite gratuite atteinte</div>'
                    '<div style="font-size:13px;color:var(--subtext);">Abonnez-vous pour un accès illimité.</div>'
                    '</div>', unsafe_allow_html=True)
                if st.button("✨ S'abonner à 2,99€/mois", type="primary"):
                    _goto("abonnement")
                return
            st.markdown(f'<div style="margin-bottom:16px;">{_badge(f"Compte gratuit · {reste} recherche(s) restante(s)","yellow")}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="margin-bottom:16px;">{_badge("✨ Abonné · Recherches illimitées","mauve")}</div>', unsafe_allow_html=True)

    col_form, col_log = st.columns([1, 1], gap="large")

    with col_form:
        st.markdown('<div class="card card-accent">', unsafe_allow_html=True)
        sujet  = st.text_area("Sujets de recherche",
                               placeholder="ex: cybersécurité IA, deepfake, LLM Europe",
                               height=90, key="sujet_input")
        c1, c2 = st.columns(2)
        with c1:
            limite = st.number_input("Articles max à résumer", min_value=1, max_value=50, value=10, step=1)
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            btn_rechercher = st.button(
                "🔍 Rechercher", use_container_width=True,
                disabled=st.session_state["en_cours"],
                type="primary", key="btn_rechercher")
        with c2:
            if st.button("🗑 Réinitialiser", use_container_width=True, key="btn_reset_veille"):
                st.session_state["logs"]               = []
                st.session_state["resultats"]          = []
                st.session_state["recherche_terminee"] = False
                st.session_state["derniere_publication"] = None
                st.rerun()

        if st.session_state["resultats"] and not st.session_state["en_cours"]:
            st.markdown("---")
            nb_r = len(st.session_state["resultats"])
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">'
                f'<span style="font-family:Space Mono;font-size:13px;">Résultats</span>'
                f'{_badge(f"{nb_r} articles trouvés","green")}</div>',
                unsafe_allow_html=True)
            for r in st.session_state["resultats"][:8]:
                dom   = urlparse(r.get("href", "")).netloc
                score = r.get("score", 0)
                c     = "green" if score >= 80 else "yellow" if score >= 50 else "red"
                st.markdown(
                    f'<div class="card" style="padding:10px 14px;margin-bottom:6px;">'
                    f'<div style="font-size:13px;font-weight:500;margin-bottom:3px;">{r.get("title","")[:72]}…</div>'
                    f'<div style="display:flex;gap:8px;">'
                    f'<span style="font-size:11px;color:var(--subtext)">{dom}</span>'
                    f'{_badge(f"score {score}",c)}</div></div>',
                    unsafe_allow_html=True)
            if nb_r > 8:
                st.caption(f"… et {nb_r - 8} autres articles")

    with col_log:
        if st.session_state["en_cours"]:
            sujet_affiche = st.session_state.get("sujet_courant", "…")
            dernier_log   = st.session_state.get("dernier_log", "Initialisation…")
            st.markdown(f"""
            <div class="launch-overlay">
                <div class="scan-line"></div>
                <div class="launch-icon-wrap">
                    <span class="launch-icon">🔭</span>
                    <div class="pulse-ring"></div><div class="pulse-ring"></div><div class="pulse-ring"></div>
                </div>
                <div class="launch-title">RECHERCHE EN COURS</div>
                <div class="launch-subject">« {sujet_affiche} »</div>
                <div class="launch-steps">
                    <div class="launch-step"><span class="step-icon">🔍</span><span class="step-label">DuckDuckGo</span></div>
                    <div class="launch-step"><span class="step-icon">📡</span><span class="step-label">Flux RSS</span></div>
                    <div class="launch-step"><span class="step-icon">⚙️</span><span class="step-label">Scoring</span></div>
                    <div class="launch-step"><span class="step-icon">🧹</span><span class="step-label">Dédup.</span></div>
                </div>
                <div class="typing-dots"><span></span><span></span><span></span></div>
                <div class="launch-status">{dernier_log}</div>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown(
                '<div style="font-family:Space Mono;font-size:12px;color:var(--subtext);'
                'text-transform:uppercase;letter-spacing:1px;margin-bottom:10px;">— Journal</div>',
                unsafe_allow_html=True)
            log_html = "<br>".join(
                st.session_state["logs"][-40:]
                if st.session_state["logs"]
                else ["<span style='color:var(--subtext)'>En attente de lancement…</span>"])
            st.markdown(f'<div class="log-box">{log_html}</div>', unsafe_allow_html=True)

    if btn_rechercher and sujet.strip() and not st.session_state["en_cours"]:
        ok_sujet, msg_sujet = security.valider_texte_recherche(sujet, longueur_max=300)
        if not ok_sujet:
            st.error(msg_sujet)
            return
        if AUTH_OK and uid:
            ok_q, msg_q = auth.peut_rechercher(uid)
            if not ok_q:
                st.error(msg_q)
                return
        st.session_state.update({
            "en_cours":           True,
            "resultats":          [],
            "sujet_courant":      sujet.strip(),
            "limite_courante":    int(limite),
            "logs":               [],
            "dernier_log":        "Initialisation…",
            "recherche_terminee": False,
            "derniere_publication": None,
        })
        st.rerun()

    elif st.session_state["en_cours"] and st.session_state.get("sujet_courant"):
        sujet_run = st.session_state["sujet_courant"]
        try:
            resultats = srv.rechercher(sujet_run, callback_statut=_log)
            st.session_state["resultats"] = resultats
            _log(f"✅ {len(resultats)} résultats trouvés — prêt à publier")
            if AUTH_OK and uid and not abonne:
                auth.incrementer_quota(uid)
        except Exception as e:
            _log(f"❌ Erreur : {e}")
        st.session_state["en_cours"]           = False
        st.session_state["dernier_log"]        = ""
        st.session_state["recherche_terminee"] = True
        st.rerun()

    elif btn_rechercher and not sujet.strip():
        st.warning("Entrez au moins un sujet.")

    if st.session_state.get("recherche_terminee") and st.session_state["resultats"] and not st.session_state["en_cours"]:
        _render_panneau_publication(uid, abonne)

    if not st.session_state["en_cours"]:
        _render_theme_editor()


def _render_panneau_publication(uid, abonne):
    nb_r   = len(st.session_state["resultats"])
    limite = st.session_state.get("limite_courante", 10)
    sujet  = st.session_state.get("sujet_courant", "")

    st.markdown("---")
    st.markdown(
        '<div style="font-family:Space Mono;font-size:14px;color:var(--green);margin-bottom:4px;">'
        '✅ Recherche terminée — choisissez où publier</div>',
        unsafe_allow_html=True)
    st.markdown(
        f'<div style="font-size:12px;color:var(--subtext);margin-bottom:16px;">'
        f'{nb_r} articles trouvés pour <strong style="color:var(--text)">{sujet}</strong>. '
        f'Les résumés IA seront générés au moment de la publication.</div>',
        unsafe_allow_html=True)

    col_p1, col_p2 = st.columns(2)
    with col_p1:
        nb_articles = st.number_input(
            "Articles à résumer et publier",
            min_value=1, max_value=min(nb_r, 50),
            value=min(limite, nb_r),
            step=1, key="pub_nb_articles")
    with col_p2:
        mode_pub = st.selectbox(
            "Mode WordPress", ["Mise à jour page", "Créer un post"], key="pub_mode")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    col_b1, col_b2, col_b3 = st.columns(3)

    with col_b1:
        btn_wp = st.button("🌐 Publier sur WordPress", use_container_width=True,
                           key="btn_pub_wp", disabled=st.session_state.get("en_cours_pub", False))
    with col_b2:
        btn_ftp = st.button("📡 Publier sur FTP", use_container_width=True,
                            key="btn_pub_ftp", disabled=st.session_state.get("en_cours_pub", False))
    with col_b3:
        btn_both = st.button("🚀 Publier partout", use_container_width=True, type="primary",
                             key="btn_pub_both", disabled=st.session_state.get("en_cours_pub", False))

    pub = st.session_state.get("derniere_publication")
    if pub:
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            ok  = pub.get("ok_wp")
            msg = pub.get("msg_wp", "")
            if ok is not None:
                ic = "✅" if ok else "❌"
                cl = "var(--green)" if ok else "var(--red)"
                st.markdown(
                    f'<div class="card" style="border-left:3px solid {cl};padding:12px 14px;margin-top:8px;">'
                    f'<div style="font-size:12px;font-weight:600;color:{cl};">{ic} WordPress</div>'
                    f'<div style="font-size:12px;color:var(--subtext);margin-top:4px;">{msg}</div>'
                    f'</div>', unsafe_allow_html=True)
        with col_r2:
            ok  = pub.get("ok_ftp")
            msg = pub.get("msg_ftp", "")
            if ok is not None:
                ic = "✅" if ok else "❌"
                cl = "var(--green)" if ok else "var(--red)"
                st.markdown(
                    f'<div class="card" style="border-left:3px solid {cl};padding:12px 14px;margin-top:8px;">'
                    f'<div style="font-size:12px;font-weight:600;color:{cl};">{ic} FTP / Page web</div>'
                    f'<div style="font-size:12px;color:var(--subtext);margin-top:4px;">{msg}</div>'
                    f'</div>', unsafe_allow_html=True)

    cible_wp  = btn_wp  or btn_both
    cible_ftp = btn_ftp or btn_both

    if (cible_wp or cible_ftp) and not st.session_state.get("en_cours_pub", False):
        st.session_state["en_cours_pub"] = True
        pub_result = {"ok_wp": None, "msg_wp": "", "ok_ftp": None, "msg_ftp": ""}

        with st.spinner("Génération des résumés IA et publication…"):
            try:
                if mode_pub == "Mise à jour page" or cible_ftp:
                    res = srv.workflow_publier(
                        sujet,
                        st.session_state["resultats"],
                        callback_statut=_log,
                        limite=int(nb_articles),
                    )
                    if "wordpress" in res:
                        pub_result["ok_wp"]  = res["wordpress"][0]
                        pub_result["msg_wp"] = res["wordpress"][1]
                    if "ftp" in res:
                        pub_result["ok_ftp"]  = res["ftp"][0]
                        pub_result["msg_ftp"] = res["ftp"][1]
                elif mode_pub == "Créer un post" and cible_wp:
                    ok, msg = srv.workflow_creer_post(
                        sujet,
                        st.session_state["resultats"][:int(nb_articles)],
                        callback_statut=_log)
                    pub_result["ok_wp"]  = ok
                    pub_result["msg_wp"] = msg
            except Exception as e:
                _log(f"❌ Erreur publication : {e}")
                pub_result["msg_wp"]  = f"Erreur : {e}"
                pub_result["msg_ftp"] = f"Erreur : {e}"

        st.session_state["derniere_publication"] = pub_result
        st.session_state["en_cours_pub"]         = False
        st.rerun()

# ============================================================
# PAGE HISTORIQUE
# ============================================================
def page_historique():
    st.markdown("# 📚 Historique des veilles")
    st.markdown("---")
    h = _historique()
    sujets = [k for k in h if not k.startswith("__") and isinstance(h[k], list)]
    if not sujets:
        st.info("Aucun historique. Lancez une première veille.")
        return
    col_g, col_d = st.columns([1, 2], gap="large")
    with col_g:
        sujet_sel = st.selectbox("Sujet à afficher", sujets, key="hist_sujet_sel")
        sessions  = h.get(sujet_sel, [])
        st.markdown(
            f'<div class="metric-box" style="margin:12px 0;">'
            f'<span class="metric-val">{len(sessions)}</span>'
            f'<span class="metric-lbl">Sessions</span></div>', unsafe_allow_html=True)
        st.markdown("---")
        st.markdown("#### Supprimer des sujets")
        sujets_a_supprimer = st.multiselect(
            "Sélectionnez les sujets à supprimer", options=sujets, default=[],
            key="sujets_suppr", placeholder="Choisissez un ou plusieurs sujets…")
        if sujets_a_supprimer:
            st.markdown(
                f'<div style="font-size:12px;color:var(--red);margin:6px 0;">'
                f'⚠️ {len(sujets_a_supprimer)} sujet(s) sélectionné(s)</div>', unsafe_allow_html=True)
            if st.button(f"🗑 Supprimer {len(sujets_a_supprimer)} sujet(s)",
                         type="secondary", use_container_width=True, key="btn_suppr_sel"):
                for s in sujets_a_supprimer:
                    _effacer_sujet(s)
                st.success(f"{len(sujets_a_supprimer)} sujet(s) supprimé(s).")
                st.rerun()
        st.markdown("---")
        with st.expander("⚠️ Tout effacer"):
            if st.button("🗑 Effacer tout", type="secondary", use_container_width=True, key="btn_eff_tout"):
                _effacer_tout()
                st.success("Historique effacé.")
                st.rerun()
    with col_d:
        for i, session in enumerate(sessions):
            if not isinstance(session, dict):
                continue
            date_s   = session.get("date", "?")
            articles = session.get("articles", [])
            rg       = session.get("resume_global", "")
            with st.expander(f"📅 {date_s} — {len(articles)} articles", expanded=(i == 0)):
                if rg and not rg.startswith("Erreur"):
                    rg_affiche = rg[:1200] + ("…" if len(rg) > 1200 else "")
                    st.markdown(
                        f'<div class="card" style="border-left:3px solid var(--yellow);margin-bottom:16px;">'
                        f'<div style="font-size:12px;font-weight:600;color:var(--yellow);margin-bottom:8px;">SYNTHÈSE</div>'
                        f'<div style="font-size:13px;line-height:1.7;">{rg_affiche}</div></div>',
                        unsafe_allow_html=True)
                for a in sorted(articles, key=lambda x: x.get("score", 0), reverse=True):
                    dom    = urlparse(a.get("href", "")).netloc
                    score  = a.get("score", 0)
                    points = a.get("resume_ollama", [])
                    pts_html = ""
                    if points and points != ["Contenu non accessible pour ce site."]:
                        pts_html = "".join(
                            f'<li style="font-size:12px;color:var(--subtext);margin:3px 0">{p}</li>'
                            for p in points[:3])
                        pts_html = f"<ul style='padding-left:18px;margin:6px 0 0 0'>{pts_html}</ul>"
                    st.markdown(
                        f'<div class="card" style="padding:12px 16px;margin-bottom:6px;">'
                        f'<div style="display:flex;justify-content:space-between;">'
                        f'<a href="{a.get("href","")}" target="_blank" style="color:var(--blue);font-size:13px;font-weight:500">{a.get("title","")[:80]}</a>'
                        f'<span class="badge badge-blue">{score}</span></div>'
                        f'<div style="font-size:11px;color:var(--subtext);margin-top:4px">{dom}</div>'
                        f'{pts_html}</div>', unsafe_allow_html=True)

# ============================================================
# PAGE COMPARAISON
# ============================================================
def page_comparaison():
    st.markdown("# 📊 Comparaison de sessions")
    st.markdown("---")
    h = _historique()
    sujets = [k for k in h if not k.startswith("__") and isinstance(h[k], list)]
    if not sujets:
        st.info("Aucun historique.")
        return
    sujet_sel = st.selectbox("Sujet", sujets)
    sessions  = [s for s in h.get(sujet_sel, []) if isinstance(s, dict)]
    if len(sessions) < 2:
        st.warning("Il faut au moins 2 sessions.")
        return
    dates = [s.get("date", f"Session {i+1}") for i, s in enumerate(sessions)]
    c1, c2 = st.columns(2)
    with c1:
        date_rec = st.selectbox("Session récente", dates, index=0)
    with c2:
        date_anc = st.selectbox("Session précédente", dates, index=min(1, len(dates)-1))
    if date_rec == date_anc:
        st.warning("Choisissez deux sessions différentes.")
        return
    sess_rec = next((s for s in sessions if s.get("date") == date_rec), None)
    sess_anc = next((s for s in sessions if s.get("date") == date_anc), None)
    if not sess_rec or not sess_anc:
        st.error("Sessions introuvables.")
        return
    hrefs_anc = {a["href"] for a in sess_anc.get("articles", []) if "href" in a}
    hrefs_rec = {a["href"] for a in sess_rec.get("articles", []) if "href" in a}
    nouveaux  = hrefs_rec - hrefs_anc
    disparus  = hrefs_anc - hrefs_rec
    c1, c2, c3 = st.columns(3)
    for col, val, lbl, clr in [
        (c1, len(sess_rec.get("articles", [])), "Récents",  "blue"),
        (c2, len(nouveaux),                     "Nouveaux", "green"),
        (c3, len(disparus),                     "Disparus", "red"),
    ]:
        with col:
            st.markdown(
                f'<div class="metric-box"><span class="metric-val" style="color:var(--{clr})">{val}</span>'
                f'<span class="metric-lbl">{lbl}</span></div>', unsafe_allow_html=True)
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    if st.button("🧠 Générer l'analyse", type="primary"):
        with st.spinner("Analyse IA…"):
            try:
                analyse = srv.comparer_sessions(sujet_sel, sess_rec, sess_anc)
                st.markdown(
                    f'<div class="card card-accent" style="margin-top:16px;">'
                    f'<div style="font-size:12px;font-weight:600;color:var(--mauve);margin-bottom:12px;">ANALYSE COMPARATIVE</div>'
                    f'<div style="font-size:13px;line-height:1.8;white-space:pre-line">{analyse}</div></div>',
                    unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Erreur : {e}")

# ============================================================
# PAGE CONFIG — avec onglet Intégration
# ============================================================
def page_config():
    st.markdown("# ⚙️ Configuration")
    st.markdown("---")
    cfg = _cfg()

    # Récupère l'URL FTP configurée pour les exemples de code
    ftp_url = cfg.get("ftp_path", "/htdocs/veille-ia.html")
    # Tente de reconstruire une URL publique à partir du host FTP
    ftp_host = cfg.get("ftp_host", "")
    # URL exemple pour les snippets (on utilise le host si dispo)
    exemple_url = f"https://{ftp_host}/veille-ia.html" if ftp_host else "https://monsite.com/veille-ia.html"

    tab_wp, tab_ftp, tab_integration = st.tabs(["🌐 WordPress", "📡 FTP", "🔗 Intégration"])

    # ── Onglet WordPress ──────────────────────────────────────
    with tab_wp:
        st.markdown("#### Connexion WordPress")
        wp_base = st.text_input("URL du site", value=cfg.get("wp_base", ""), placeholder="https://monsite.com")
        c1, c2  = st.columns(2)
        with c1:
            wp_user = st.text_input("Identifiant", value=cfg.get("wp_user", ""))
        with c2:
            wp_pwd = st.text_input("Mot de passe app", value=cfg.get("wp_password", ""), type="password")
        cs, ct = st.columns(2)
        with cs:
            if st.button("💾 Sauvegarder", use_container_width=True):
                cfg.update({"wp_base": wp_base, "wp_user": wp_user, "wp_password": wp_pwd})
                _save_cfg(cfg)
                st.success("Sauvegardé !")
        with ct:
            if st.button("🔌 Tester WP", use_container_width=True):
                ok, msg = srv.tester_connexion_wp(wp_base, wp_user, wp_pwd)
                st.success(msg) if ok else st.error(msg)

    # ── Onglet FTP ────────────────────────────────────────────
    with tab_ftp:
        st.markdown("#### Connexion FTP")
        ftp_host_input = st.text_input("Hôte FTP", value=cfg.get("ftp_host", ""))
        c1, c2         = st.columns(2)
        with c1:
            ftp_user = st.text_input("Utilisateur FTP", value=cfg.get("ftp_user", ""))
        with c2:
            ftp_pwd = st.text_input("Mot de passe FTP", value=cfg.get("ftp_password", ""), type="password")
        ftp_path = st.text_input("Chemin distant", value=cfg.get("ftp_path", "/htdocs/veille-ia.html"))
        cs, ct   = st.columns(2)
        with cs:
            if st.button("💾 Sauvegarder FTP", use_container_width=True):
                cfg.update({"ftp_host": ftp_host_input, "ftp_user": ftp_user,
                            "ftp_password": ftp_pwd, "ftp_path": ftp_path})
                _save_cfg(cfg)
                st.success("Sauvegardé !")
        with ct:
            if st.button("🔌 Tester FTP", use_container_width=True):
                ok, msg = srv.tester_connexion_ftp(ftp_host_input, ftp_user, ftp_pwd)
                st.success(msg) if ok else st.error(msg)

    # ── Onglet Intégration ────────────────────────────────────
    with tab_integration:
        st.markdown("#### 🔗 Intégrer la veille sur une autre page")
        st.markdown(
            '<div style="font-size:13px;color:var(--subtext);margin-bottom:20px;">'
            'Une fois votre veille publiée sur FTP, vous pouvez l\'afficher sur n\'importe quelle page '
            'web (WordPress, site perso, etc.) en copiant l\'un des snippets ci-dessous.'
            '</div>', unsafe_allow_html=True)

        # Champ URL personnalisable
        url_veille = st.text_input(
            "URL publique de votre veille-ia.html",
            value=exemple_url,
            placeholder="https://monsite.com/veille-ia.html",
            key="integration_url",
            help="C'est l'URL où votre fichier veille-ia.html est accessible publiquement.")

        st.markdown("---")

        # ── Méthode 1 : iframe responsive ─────────────────────
        st.markdown(
            '<div style="font-family:Space Mono;font-size:12px;color:var(--blue);margin-bottom:8px;">'
            '▶ Méthode 1 — iframe responsive (recommandée)</div>', unsafe_allow_html=True)
        st.markdown(
            '<div style="font-size:12px;color:var(--subtext);margin-bottom:8px;">'
            'Collez ce code dans la page ou l\'article WordPress où vous voulez afficher la veille. '
            'L\'iframe s\'ajuste automatiquement à la hauteur du contenu et ignore le cache.</div>',
            unsafe_allow_html=True)

        code_iframe = f"""<div id="veille-container"></div>
<script>
var url = "{url_veille}?v=" + Date.now();
document.getElementById("veille-container").innerHTML =
  '<iframe src="' + url + '" style="width:100%;border:none;" ' +
  'onload="this.style.height=this.contentDocument.body.scrollHeight+\'px\'"></iframe>';
</script>"""
        st.code(code_iframe, language="html")

        st.markdown(
            '<div style="font-size:11px;color:var(--subtext);margin-top:4px;margin-bottom:20px;">'
            '💡 Le <code>?v=Date.now()</code> force le rechargement à chaque visite — '
            'votre lecteur voit toujours la version la plus récente.</div>',
            unsafe_allow_html=True)

        # ── Méthode 2 : iframe simple ──────────────────────────
        st.markdown(
            '<div style="font-family:Space Mono;font-size:12px;color:var(--blue);margin-bottom:8px;">'
            '▶ Méthode 2 — iframe simple (hauteur fixe)</div>', unsafe_allow_html=True)
        st.markdown(
            '<div style="font-size:12px;color:var(--subtext);margin-bottom:8px;">'
            'Version simplifiée si la méthode 1 pose problème. '
            'Ajustez la hauteur selon votre contenu.</div>',
            unsafe_allow_html=True)

        code_iframe_simple = f"""<iframe
  src="{url_veille}?v=TIMESTAMP"
  style="width:100%; height:1800px; border:none;"
  loading="lazy">
</iframe>"""
        st.code(code_iframe_simple, language="html")

        st.markdown(
            '<div style="font-size:11px;color:var(--subtext);margin-top:4px;margin-bottom:20px;">'
            '💡 Remplacez <code>TIMESTAMP</code> par un nombre qui change à chaque mise à jour '
            '(ex: la date du jour) pour forcer le rechargement.</div>',
            unsafe_allow_html=True)

        # ── Méthode 3 : lien direct ────────────────────────────
        st.markdown(
            '<div style="font-family:Space Mono;font-size:12px;color:var(--blue);margin-bottom:8px;">'
            '▶ Méthode 3 — lien direct vers la page</div>', unsafe_allow_html=True)
        st.markdown(
            '<div style="font-size:12px;color:var(--subtext);margin-bottom:8px;">'
            'La solution la plus simple : un lien ou un bouton qui ouvre la page dans un nouvel onglet.</div>',
            unsafe_allow_html=True)

        code_lien = f"""<a href="{url_veille}" target="_blank"
   style="display:inline-block;padding:10px 20px;
          background:#89b4fa;color:#1e1e2e;
          border-radius:8px;font-weight:bold;
          text-decoration:none;">
  📡 Voir la veille technologique
</a>"""
        st.code(code_lien, language="html")

        st.markdown("---")

        # ── Note WordPress ─────────────────────────────────────
        st.markdown(
            '<div class="card card-accent" style="padding:14px 16px;">'
            '<div style="font-size:13px;font-weight:600;color:var(--blue);margin-bottom:8px;">📝 Note WordPress</div>'
            '<div style="font-size:12px;color:var(--subtext);line-height:1.8;">'
            'WordPress filtre le HTML par défaut. Pour que les snippets fonctionnent :<br>'
            '• Utilisez l\'éditeur en mode <strong style="color:var(--text)">HTML / Code source</strong> (pas Gutenberg visuel)<br>'
            '• Ou installez le plugin <strong style="color:var(--text)">WPCode</strong> pour injecter du HTML/JS proprement<br>'
            '• Ou ajoutez le code dans un bloc <strong style="color:var(--text)">HTML personnalisé</strong> (Custom HTML block)'
            '</div></div>',
            unsafe_allow_html=True)

    # ── Infos stockage ────────────────────────────────────────
    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        mode_s = "Supabase ☁️" if (STORAGE_OK and getattr(storage, "SUPABASE_OK", False)) else "Fichier local 💾"
        st.markdown(
            f'<div class="card"><div style="font-size:11px;color:var(--subtext)">Stockage</div>'
            f'<div style="font-size:13px;font-weight:500;margin-top:4px">{mode_s}</div></div>',
            unsafe_allow_html=True)
    with c2:
        h    = _historique()
        nb_s = sum(1 for k in h if not k.startswith("__"))
        nb_a = sum(len(s.get("articles", [])) for ss in h.values() if isinstance(ss, list) for s in ss if isinstance(s, dict))
        st.markdown(
            f'<div class="card"><div style="font-size:12px;color:var(--subtext)">Historique</div>'
            f'<div style="font-size:12px;margin-top:4px">{nb_s} sujets · {nb_a} articles</div></div>',
            unsafe_allow_html=True)

# ============================================================
# PAGE CONFORMITE RGPD
# ============================================================
def page_conformite():
    st.markdown("# 🛡️ Conformité & RGPD")
    st.markdown("### Informations sur la protection des données")
    st.markdown("---")

    st.info(
        "Cette page est un modele informatif a personnaliser avec vos informations "
        "legales definitives (raison sociale, DPO, hebergeur, durees exactes, etc.)."
    )

    with st.expander("1) Responsable du traitement", expanded=True):
        st.markdown(
            "- **Editeur du service** : `lucas rajany`\n"
            "- **Contact** : `lucas.rajanysio@gmail.com`\n"
            "- **Delegue a la protection des donnees (DPO)** : `A COMPLETER`"
        )

    with st.expander("2) Donnees collectees"):
        st.markdown(
            "- Donnees de compte : email, identifiant utilisateur.\n"
            "- Donnees de configuration : preferences veille, integrations (WordPress/FTP).\n"
            "- Donnees de contenu : sujets, resultats, historique de veille.\n"
            "- Donnees techniques : journaux techniques de fonctionnement."
        )

    with st.expander("3) Finalites du traitement"):
        st.markdown(
            "- Fournir le service de veille et l'historique.\n"
            "- Generer des resumes et syntheses IA.\n"
            "- Publier les contenus sur les integrations choisies.\n"
            "- Envoyer des emails automatiques si active."
        )

    with st.expander("4) Base legale"):
        st.markdown(
            "- **Consentement** : t'a dit oui t'es finito maintenant.\n"
            "- **Interet legitime** : securite, prevention des abus et amelioration du service."
        )

    with st.expander("5) Duree de conservation"):
        st.markdown(
            "- Compte utilisateur : pendant la duree d'utilisation, puis archivage/suppression selon politique interne.\n"
            "- Historique de veille : jusqu'a suppression par l'utilisateur ou expiration de la retention.\n"
            "- Logs techniques : conservation limitee pour securite et diagnostic."
        )

    with st.expander("6) Destinataires et sous-traitants"):
        st.markdown(
            "- Hebergement / base de donnees : Supabase.\n"
            "- Services IA : Groq.\n"
            "- Integrations tierces : WordPress, FTP, fournisseur email.\n"
            "- Chaque sous-traitant applique ses propres mesures de securite et de conformite."
        )

    with st.expander("7) Droits des personnes"):
        st.markdown(
            "Vous pouvez exercer vos droits d'acces, rectification, effacement, "
            "limitation, opposition et portabilite via : `lucas.rajanysio@gmail.com`."
        )

    with st.expander("8) Securite"):
        st.markdown(
            "- Controle d'acces aux comptes.\n"
            "- Stockage segmente par utilisateur.\n"
            "- Mesures techniques et organisationnelles de securite."
        )

    with st.expander("9) Cookies et traceurs"):
        st.markdown(
            "tu veux un cookie ^-^ ?"
        )

    st.markdown("---")

# ============================================================
# PAGE CONDITIONS D'UTILISATION
# ============================================================
def page_conditions():
    st.markdown("# 📄 Conditions d'utilisation")
    st.markdown("### Acceptation obligatoire pour utiliser la plateforme")
    st.markdown("---")

    st.markdown(
        """
En utilisant Veille IA, vous acceptez notamment que :

- Le service collecte les donnees necessaires au fonctionnement (compte, configuration, historique).
- Les contenus analyses peuvent etre traites par des services tiers (ex: IA, email, hebergement).
- Vous restez responsable des publications effectuees vers WordPress/FTP.
- Le service est fourni "en l'etat" et peut evoluer dans le temps.
- Vous pouvez demander la suppression de vos donnees selon la politique en vigueur.
        """
    )

    st.info("j'ai pas de condition juste dite bonjour.")

    uid = _user_id()
    if _conditions_acceptees():
        st.success("Conditions deja acceptees.")
        if st.button("Retour", type="primary"):
            _goto("veille")
        return

    cgu_ok = st.checkbox("J'ai lu et j'accepte les Conditions d'utilisation.")
    if st.button("✅ Accepter et continuer", type="primary", disabled=not cgu_ok):
        if not AUTH_OK or not uid:
            st.error("Session invalide. Reconnectez-vous.")
            return
        res = auth.accepter_conditions(uid)
        if res.get("ok"):
            st.session_state["profil"] = auth.get_profil(uid)
            st.success("Merci, vos conditions ont ete enregistrees.")
            _goto("veille")
        else:
            st.error(res.get("message", "Erreur lors de l'enregistrement."))

# ============================================================
# ROUTING PRINCIPAL
# ============================================================
user = st.session_state.get("user")

if user:
    _activer_storage(user.id)
    try:
        cfg_saved = _cfg()
        if "theme_ftp" in cfg_saved and isinstance(cfg_saved["theme_ftp"], str):
            saved = json.loads(cfg_saved["theme_ftp"])
            if st.session_state["theme_widget_version"] == 0:
                st.session_state["theme_ftp"].update(saved)
    except Exception:
        pass

render_sidebar()

page = st.session_state["page"]

if not user:
    page_accueil()
else:
    if AUTH_OK and not _conditions_acceptees():
        page_conditions()
    else:
        if   page == "veille":      page_veille()
        elif page == "historique":  page_historique()
        elif page == "comparaison": page_comparaison()
        elif page == "auto":        page_auto()
        elif page == "config":      page_config()
        elif page == "abonnement":  page_abonnement()
        elif page == "conditions":  page_conditions()
        elif page == "conformite":  page_conformite()
        else:                       page_veille()