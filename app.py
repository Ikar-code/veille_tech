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
except Exception:
    pass

import serveur as srv
import chatbot

# ── Auth (optionnel) ──────────────────────────────────────
AUTH_OK = False
try:
    import auth
    AUTH_OK = True
except Exception as e:
    print(f"[app] module auth indisponible: {e}")

# ── Storage (optionnel) ───────────────────────────────────
STORAGE_OK = False
try:
    import storage
    STORAGE_OK = True
except Exception as e:
    print(f"[app] module storage indisponible: {e}")

# ── Security (optionnel) ──────────────────────────────────
SECURITY_OK = False
try:
    import security
    SECURITY_OK = True
except Exception:
    pass

def _valider_texte(texte: str, longueur_max: int = 500):
    if SECURITY_OK:
        try:
            return security.valider_texte_recherche(texte, longueur_max=longueur_max)
        except Exception:
            pass
    texte = texte.strip()
    if not texte:
        return False, "Le champ ne peut pas être vide."
    if len(texte) > longueur_max:
        return False, f"Texte trop long ({len(texte)} > {longueur_max} caractères)."
    return True, ""

st.set_page_config(
    page_title="Veille IA",
    page_icon="🔭",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');
:root{--bg:#1e1e2e;--surface:#181825;--overlay:#313244;--text:#cdd6f4;--subtext:#a6adc8;--blue:#89b4fa;--yellow:#f9e2af;--green:#a6e3a1;--red:#f38ba8;--mauve:#cba6f7;--border:#45475a;}
.stApp{background:var(--bg);font-family:'DM Sans',sans-serif;color:var(--text);}
.stApp>header{background:transparent!important;}
[data-testid="stSidebar"]{background:var(--surface)!important;border-right:1px solid var(--border);}
[data-testid="stSidebar"] .stMarkdown h2{font-family:'Space Mono',monospace;font-size:13px;color:var(--blue);letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid var(--border);padding-bottom:8px;margin-bottom:12px;}
h1,h2,h3{font-family:'Space Mono',monospace!important;color:var(--text)!important;}
h1{font-size:22px!important;letter-spacing:1px;}h3{font-size:14px!important;color:var(--subtext)!important;font-weight:400!important;}
.stTextInput>div>div>input,.stTextArea textarea,.stNumberInput input{background:var(--overlay)!important;border:1px solid var(--border)!important;color:var(--text)!important;border-radius:8px!important;}
.stTextInput>div>div>input:focus,.stTextArea textarea:focus{border-color:var(--blue)!important;box-shadow:0 0 0 2px rgba(137,180,250,.15)!important;}
.stButton>button{background:var(--overlay)!important;color:var(--text)!important;border:1px solid var(--border)!important;border-radius:8px!important;font-weight:500!important;transition:all .15s ease!important;padding:.5rem 1.2rem!important;}
.stButton>button:hover{background:var(--blue)!important;color:var(--bg)!important;border-color:var(--blue)!important;}
.stTabs [data-baseweb="tab-list"]{background:var(--surface);border-radius:10px;padding:4px;gap:4px;border-bottom:none!important;}
.stTabs [data-baseweb="tab"]{background:transparent!important;color:var(--subtext)!important;border-radius:8px!important;font-size:13px!important;padding:8px 16px!important;border:none!important;}
.stTabs [aria-selected="true"]{background:var(--overlay)!important;color:var(--blue)!important;}
.card{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:20px;margin-bottom:12px;}
.card-accent{border-left:3px solid var(--blue);}.card-green{border-left:3px solid var(--green);}.card-red{border-left:3px solid var(--red);}.card-mauve{border-left:3px solid var(--mauve);}
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
::-webkit-scrollbar{width:6px;}::-webkit-scrollbar-track{background:var(--surface);}::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px;}
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

/* ════════════════════════════════════════
   CHATBOT WIDGET FLOTTANT
   ════════════════════════════════════════ */
.chat-fab-wrap{
    position:fixed;bottom:28px;right:28px;z-index:9999;
}
.chat-fab{
    width:56px;height:56px;border-radius:50%;
    background:linear-gradient(135deg,#89b4fa,#cba6f7);
    color:#1e1e2e;border:none;cursor:pointer;
    font-size:24px;font-weight:700;
    box-shadow:0 4px 24px rgba(137,180,250,.45);
    display:flex;align-items:center;justify-content:center;
    transition:transform .2s,box-shadow .2s;
}
.chat-fab:hover{transform:scale(1.12);box-shadow:0 6px 32px rgba(137,180,250,.65);}
.chat-window{
    position:fixed;bottom:96px;right:28px;
    width:360px;max-width:calc(100vw - 56px);
    background:#181825;border:1px solid #45475a;
    border-radius:18px;box-shadow:0 12px 48px rgba(0,0,0,.55);
    z-index:9998;display:flex;flex-direction:column;
    overflow:hidden;
    animation:chat-pop .18s cubic-bezier(.34,1.56,.64,1);
}
@keyframes chat-pop{
    from{opacity:0;transform:translateY(16px) scale(.95)}
    to{opacity:1;transform:none}
}
.chat-header{
    padding:14px 16px;
    background:linear-gradient(135deg,#313244,#1e1e2e);
    border-bottom:1px solid #45475a;
    display:flex;align-items:center;gap:10px;
    flex-shrink:0;
}
.chat-avatar{
    width:34px;height:34px;border-radius:50%;
    background:linear-gradient(135deg,#89b4fa,#cba6f7);
    color:#1e1e2e;display:flex;align-items:center;
    justify-content:center;font-size:17px;font-weight:700;
    flex-shrink:0;
}
.chat-header-name{font-size:13px;font-weight:600;color:#cdd6f4;}
.chat-header-status{font-size:11px;color:#a6e3a1;margin-top:1px;}
.chat-header-close{
    margin-left:auto;background:none;border:none;
    color:#a6adc8;cursor:pointer;font-size:18px;
    line-height:1;padding:2px 4px;border-radius:4px;
    transition:color .15s;
}
.chat-header-close:hover{color:#cdd6f4;}
.chat-messages{
    flex:1;min-height:220px;max-height:280px;
    overflow-y:auto;padding:12px;
    display:flex;flex-direction:column;gap:8px;
    scroll-behavior:smooth;
}
.chat-messages::-webkit-scrollbar{width:4px;}
.chat-messages::-webkit-scrollbar-thumb{background:#45475a;border-radius:2px;}
.cmsg{
    max-width:88%;padding:9px 13px;
    border-radius:14px;font-size:13px;line-height:1.55;
    word-break:break-word;
}
.cmsg-user{
    align-self:flex-end;
    background:linear-gradient(135deg,#89b4fa,#74c7ec);
    color:#1e1e2e;border-bottom-right-radius:4px;
    font-weight:500;
}
.cmsg-bot{
    align-self:flex-start;
    background:#313244;color:#cdd6f4;
    border-bottom-left-radius:4px;
}
.cmsg-typing{
    align-self:flex-start;
    background:#313244;color:#a6adc8;
    padding:10px 14px;border-radius:14px;
    font-size:13px;border-bottom-left-radius:4px;
}
.chat-suggestions{
    padding:8px 10px;
    display:flex;flex-wrap:wrap;gap:5px;
    border-top:1px solid #313244;flex-shrink:0;
}
.chat-sug{
    background:#313244;color:#a6adc8;
    border:1px solid #45475a;border-radius:16px;
    padding:4px 10px;font-size:11px;cursor:pointer;
    transition:all .15s;white-space:nowrap;
}
.chat-sug:hover{background:#89b4fa;color:#1e1e2e;border-color:#89b4fa;}
.chat-input-area{
    padding:10px 12px;border-top:1px solid #313244;
    display:flex;gap:8px;align-items:center;flex-shrink:0;
    background:#181825;
}
.chat-footer{
    padding:6px 12px;
    font-size:10px;color:#45475a;text-align:center;
    border-top:1px solid #313244;flex-shrink:0;
    background:#181825;
}
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
    "ptitle":"Veille Technologique IA",
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
        "theme_widget_version":0,
        "theme_ftp":dict(THEME_DEFAULT),
        "recherche_terminee":False,
        "limite_courante":10,
        "derniere_publication":None,
        # ── Chatbot ──
        "chat_ouvert":   False,
        "chat_messages": [],
        "chat_sug_used": False,
        "chat_history_loaded": False,  # flag pour ne charger qu'une fois
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()

# Restaure session Supabase si possible
if AUTH_OK and not st.session_state.get("user"):
    try:
        for fn in ["recuperer_session","rafraichir_session"]:
            if hasattr(auth, fn):
                res = getattr(auth, fn)()
                if res.get("ok"):
                    st.session_state["user"]    = res.get("user")
                    st.session_state["session"] = res.get("session")
                    try: st.session_state["profil"] = auth.get_profil(res["user"].id)
                    except Exception: pass
                    break
    except Exception:
        pass

# ── Charge l'historique chat depuis Supabase au démarrage ──
# (une seule fois par session, seulement si l'utilisateur est connecté)
_uid_actuel = st.session_state.get("user") and st.session_state["user"].id
if _uid_actuel and STORAGE_OK and not st.session_state.get("chat_history_loaded"):
    try:
        hist_chat = storage.charger_historique_chat(_uid_actuel, limite=40)
        if hist_chat:
            st.session_state["chat_messages"] = hist_chat
            st.session_state["chat_sug_used"] = True  # ne pas montrer les suggestions si historique existant
    except Exception:
        pass
    st.session_state["chat_history_loaded"] = True

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
    if not AUTH_OK: return False
    uid = _user_id()
    return auth.est_abonne(uid) if uid else False

def _conditions_acceptees():
    if not AUTH_OK: return True
    uid = _user_id()
    if not uid: return False
    profil = st.session_state.get("profil") or {}
    if "terms_accepted" in profil: return bool(profil.get("terms_accepted"))
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
        try: return storage.charger_config()
        except Exception: pass
    return srv.charger_config()

def _save_cfg(c):
    if STORAGE_OK:
        try: storage.sauvegarder_config(c); return
        except Exception: pass
    srv.sauvegarder_config(c)

def _historique():
    if STORAGE_OK:
        try: return storage.charger_historique()
        except Exception: pass
    return srv.charger_historique()

def _effacer_sujet(sujet):
    h = _historique()
    if sujet in h:
        del h[sujet]
        if STORAGE_OK:
            try: storage.sauvegarder_historique(h); return
            except Exception: pass
        srv.sauvegarder_historique(h)

def _effacer_tout():
    if STORAGE_OK:
        try: storage.effacer_historique(); return
        except Exception: pass
    srv.effacer_historique()

def _fusionner_historique_import(h_existant: dict, h_import: dict) -> dict:
    out = dict(h_existant)
    for sujet, sessions in h_import.items():
        if sujet.startswith("__") or not isinstance(sessions, list): continue
        k = sujet.strip().lower()
        if not k: continue
        if k not in out: out[k] = []
        exist_dates = {s.get("date") for s in out[k] if isinstance(s, dict)}
        for s in sessions:
            if isinstance(s, dict) and s.get("date") not in exist_dates:
                out[k].append(s); exist_dates.add(s.get("date"))
    return out

def _sauvegarder_historique_complet(h):
    if STORAGE_OK:
        try: storage.sauvegarder_historique(h); return
        except Exception: pass
    srv.sauvegarder_historique(h)

def _activer_storage(user_id):
    if STORAGE_OK and user_id:
        try: storage.set_user(user_id); srv.set_storage_context(storage)
        except Exception: pass

def _appliquer_theme(valeurs: dict):
    st.session_state["theme_ftp"].update(valeurs)
    st.session_state["theme_widget_version"] += 1

# ============================================================
# CHATBOT WIDGET FLOTTANT
# ============================================================
def render_chatbot():
    """Widget chatbot flottant en bas à droite — LLaMA via Groq avec mémoire Supabase."""

    msgs      = st.session_state["chat_messages"]
    ouvert    = st.session_state["chat_ouvert"]
    sug_used  = st.session_state["chat_sug_used"]
    uid       = _user_id()

    # ── Bouton FAB ────────────────────────────────────────────
    fab_icon  = "✕" if ouvert else "💬"
    fab_label = "Fermer le support" if ouvert else "Support Veille IA"
    st.markdown(
        f'<div class="chat-fab-wrap">'
        f'<button class="chat-fab" title="{fab_label}" '
        f'onclick="window._chatToggle()">{fab_icon}</button>'
        f'</div>',
        unsafe_allow_html=True)

    with st.form("chat_fab_form", clear_on_submit=True):
        fab_clicked = st.form_submit_button("toggle_chat", use_container_width=False)
    st.markdown("""
    <script>
    function window._chatToggle(){
        var btns = window.parent.document.querySelectorAll('button');
        for(var b of btns){
            if(b.innerText.trim()==='toggle_chat'){b.click();break;}
        }
    }
    (function hide(){
        var btns = window.parent.document.querySelectorAll('button');
        for(var b of btns){if(b.innerText.trim()==='toggle_chat'){b.style.display='none';}}
    })();
    </script>
    """, unsafe_allow_html=True)

    if fab_clicked:
        st.session_state["chat_ouvert"] = not ouvert
        st.rerun()

    if not ouvert:
        return

    # ── Fenêtre chat ─────────────────────────────────────────
    st.markdown('<div class="chat-window">', unsafe_allow_html=True)

    # En-tête
    st.markdown(
        '<div class="chat-header">'
        '<div class="chat-avatar">🔭</div>'
        '<div style="flex:1">'
        '<div class="chat-header-name">Support Veille IA</div>'
        '<div class="chat-header-status">● En ligne — LLaMA via Groq</div>'
        '</div>'
        '</div>',
        unsafe_allow_html=True)

    # Zone messages
    if not msgs:
        msgs_html = (
            '<div class="cmsg cmsg-bot">'
            '👋 Bonjour ! Je suis l\'assistant de Veille IA.<br>'
            'Pose-moi ta question ou clique sur une suggestion.'
            '</div>'
        )
    else:
        msgs_html = ""
        for m in msgs:
            cls = "cmsg-user" if m["role"] == "user" else "cmsg-bot"
            txt = m["content"].replace("<","&lt;").replace(">","&gt;").replace("\n","<br>")
            msgs_html += f'<div class="cmsg {cls}">{txt}</div>'

    st.markdown(
        f'<div class="chat-messages" id="chat-msgs">{msgs_html}</div>',
        unsafe_allow_html=True)

    # Auto-scroll
    st.markdown("""
    <script>
    (function(){
        var el = window.parent.document.getElementById('chat-msgs');
        if(el) el.scrollTop = el.scrollHeight;
    })();
    </script>""", unsafe_allow_html=True)

    # Suggestions rapides (affichées seulement si pas encore utilisées)
    if not sug_used:
        sugs = chatbot.QUESTIONS_PREDEFINIES[:4]
        st.markdown('<div class="chat-suggestions">', unsafe_allow_html=True)
        sug_cols = st.columns(len(sugs))
        for i, q in enumerate(sugs):
            with sug_cols[i]:
                if st.button(q, key=f"csug_{i}", use_container_width=True):
                    st.session_state["chat_messages"].append({"role":"user","content":q})
                    st.session_state["chat_sug_used"] = True
                    with st.spinner("…"):
                        # Utilise la mémoire Supabase si connecté, sinon fallback local
                        if uid and STORAGE_OK:
                            rep = chatbot.repondre_avec_memoire(uid, q)
                        else:
                            rep = chatbot.repondre(st.session_state["chat_messages"])
                    st.session_state["chat_messages"].append({"role":"assistant","content":rep})
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # Champ de saisie
    st.markdown('<div class="chat-input-area">', unsafe_allow_html=True)
    col_inp, col_send = st.columns([5, 1])
    with col_inp:
        user_input = st.text_input(
            "msg", label_visibility="collapsed",
            placeholder="Pose ta question…",
            key=f"chat_inp_{len(msgs)}")
    with col_send:
        envoyer = st.button("➤", key=f"chat_send_{len(msgs)}", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Traitement du message saisi
    if (envoyer or user_input) and str(user_input).strip():
        msg_txt = str(user_input).strip()
        st.session_state["chat_messages"].append({"role":"user","content":msg_txt})
        st.session_state["chat_sug_used"] = True
        # Limite l'historique local à 20 messages pour ne pas exploser le contexte Groq
        if len(st.session_state["chat_messages"]) > 20:
            st.session_state["chat_messages"] = st.session_state["chat_messages"][-20:]
        with st.spinner("…"):
            # Utilise la mémoire Supabase si connecté, sinon fallback local
            if uid and STORAGE_OK:
                rep = chatbot.repondre_avec_memoire(uid, msg_txt)
            else:
                rep = chatbot.repondre(st.session_state["chat_messages"])
        st.session_state["chat_messages"].append({"role":"assistant","content":rep})
        st.rerun()

    # Boutons secondaires
    col_cl, col_info = st.columns([1, 2])
    with col_cl:
        if st.button("🗑 Effacer", key="chat_clear", use_container_width=True):
            # Efface aussi dans Supabase si connecté
            if uid and STORAGE_OK:
                try:
                    storage.effacer_historique_chat(uid)
                except Exception:
                    pass
            st.session_state["chat_messages"] = []
            st.session_state["chat_sug_used"] = False
            st.rerun()
    with col_info:
        st.markdown(
            '<div class="chat-footer">Propulsé par LLaMA 3.1 · Groq</div>',
            unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)  # ferme .chat-window

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
                f'<div style="margin-top:6px;">{"<span class=\'badge badge-mauve\'>✨ Abonné</span>" if abonne else "<span class=\'badge badge-yellow\'>Gratuit</span>"}'
                f'</div></div>', unsafe_allow_html=True)
            if not abonne:
                st.markdown(
                    '<div style="background:rgba(203,166,247,.08);border:1px solid var(--mauve);'
                    'border-radius:10px;padding:10px;margin-bottom:12px;text-align:center;">'
                    '<div style="font-size:11px;color:var(--mauve);font-weight:600;margin-bottom:3px;">Passer à illimité</div>'
                    '<div style="font-size:20px;font-weight:700;">2,99€<span style="font-size:11px;font-weight:400;color:var(--subtext)">/mois</span></div>'
                    '</div>', unsafe_allow_html=True)
            st.markdown("---")
            st.markdown("## Navigation")
            pages = {
                "🔍 Nouvelle veille":"veille","📚 Historique":"historique",
                "📊 Comparaison":"comparaison","⏰ Automatisation":"auto",
                "⚙️ Configuration":"config","✨ Abonnement":"abonnement",
                "📄 Conditions":"conditions","🛡️ Conformité RGPD":"conformite",
            }
            for label, key in pages.items():
                actif = page == key
                if st.button(label, use_container_width=True,
                             type="primary" if actif else "secondary", key=f"sb_nav_{key}"):
                    st.session_state["page"] = key; st.rerun()
            st.markdown("---")
            if st.button("🚪 Déconnexion", use_container_width=True, key="sb_logout"):
                if AUTH_OK:
                    try: auth.deconnecter()
                    except Exception: pass
                if STORAGE_OK:
                    try: storage.set_user(None)
                    except Exception: pass
                st.session_state.update({"user":None,"session":None,"profil":{},
                    "page":"accueil","dernier_log":"","recherche_terminee":False,
                    "derniere_publication":None,"chat_messages":[],"chat_sug_used":False,
                    "chat_history_loaded":False})
                st.rerun()
        else:
            st.markdown('<div style="font-size:12px;color:var(--subtext);text-align:center;margin-bottom:12px;">Connectez-vous pour accéder à la plateforme</div>', unsafe_allow_html=True)
            if st.button("🔑 Se connecter / S'inscrire", use_container_width=True, type="primary", key="sb_login"):
                st.session_state["page"] = "accueil"; st.rerun()
            st.markdown("---")
            st.markdown('<p style="font-size:11px;color:var(--subtext);text-align:center;">Veille auto · Groq · DuckDuckGo</p>', unsafe_allow_html=True)

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
            '<div style="font-size:14px;color:var(--subtext);margin-top:10px;">Plateforme de veille académique automatisée</div>'
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
                        st.session_state.update({"user":res["user"],"session":res["session"],
                            "profil":auth.get_profil(res["user"].id),"page":"veille",
                            "chat_history_loaded":False})
                        _activer_storage(res["user"].id); st.rerun()
                    else:
                        st.error(res["message"])
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            if st.button("Mot de passe oublié ?", use_container_width=True, key="btn_reset_pwd"):
                if email:
                    res = auth.reinitialiser_mot_de_passe(email)
                    st.success(res["message"]) if res["ok"] else st.error(res["message"])
                else:
                    st.warning("Entrez votre email d'abord.")
            st.markdown("---")
            if st.button("🔵 Continuer avec Google", use_container_width=True, key="btn_google"):
                url = auth.connecter_google()
                if url: st.markdown(f'<meta http-equiv="refresh" content="0;url={url}">', unsafe_allow_html=True)
                else:   st.error("Google OAuth non configuré.")

        with tab_in:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            st.markdown(
                '<div class="card card-green" style="padding:14px 16px;margin-bottom:16px;">'
                '<div style="font-size:13px;font-weight:600;color:var(--green);margin-bottom:6px;">Offre gratuite</div>'
                '<div style="font-size:12px;color:var(--subtext);line-height:1.8;">'
                '✔ 1 recherche offerte<br>✔ Accès à l\'historique<br>✔ Sans carte bancaire</div></div>',
                unsafe_allow_html=True)
            email2 = st.text_input("Email", key="reg_email", placeholder="votre@email.com")
            pwd2   = st.text_input("Mot de passe", type="password", key="reg_pwd", help="Minimum 6 caractères")
            pwd2b  = st.text_input("Confirmer", type="password", key="reg_pwd2")
            st.markdown('<div style="font-size:11px;color:var(--subtext);margin:8px 0;">En créant un compte vous acceptez nos CGU.</div>', unsafe_allow_html=True)
            if st.button("Créer mon compte", use_container_width=True, type="primary", key="btn_register"):
                if not email2 or not pwd2:   st.error("Remplissez tous les champs.")
                elif pwd2 != pwd2b:           st.error("Les mots de passe ne correspondent pas.")
                elif len(pwd2) < 6:           st.error("Minimum 6 caractères.")
                else:
                    with st.spinner("Création…"):
                        res = auth.inscrire(email2, pwd2)
                    if res["ok"]: st.success(res["message"]); st.info("Vérifiez votre email puis connectez-vous.")
                    else:         st.error(res["message"])

# ============================================================
# ÉDITEUR DE THÈME FTP
# ============================================================
def _render_theme_editor():
    th  = st.session_state["theme_ftp"]
    ver = st.session_state["theme_widget_version"]

    st.markdown(
        '<div style="font-family:Space Mono;font-size:13px;color:var(--blue);">🎨 Personnaliser le thème de veille-ia.html</div>',
        unsafe_allow_html=True)
    st.markdown(
        '<div style="font-size:12px;color:var(--subtext);margin:6px 0 16px 0;">'
        'Modifiez l\'apparence de la page publiée sur votre hébergement FTP.</div>',
        unsafe_allow_html=True)

    PRESETS = {
        "🌙 Catppuccin":{"bg":"#1e1e2e","surf":"#181825","ov":"#313244","txt":"#cdd6f4","sub":"#a6adc8","brd":"#45475a","blue":"#89b4fa","grn":"#a6e3a1","yel":"#f9e2af","red":"#f38ba8"},
        "☀️ Light":     {"bg":"#f8f9fa","surf":"#ffffff","ov":"#e9ecef","txt":"#212529","sub":"#6c757d","brd":"#dee2e6","blue":"#0d6efd","grn":"#198754","yel":"#e67e00","red":"#dc3545"},
        "❄️ Nord":      {"bg":"#2e3440","surf":"#3b4252","ov":"#434c5e","txt":"#eceff4","sub":"#d8dee9","brd":"#4c566a","blue":"#88c0d0","grn":"#a3be8c","yel":"#ebcb8b","red":"#bf616a"},
        "🧛 Dracula":   {"bg":"#282a36","surf":"#1e1f29","ov":"#44475a","txt":"#f8f8f2","sub":"#6272a4","brd":"#44475a","blue":"#8be9fd","grn":"#50fa7b","yel":"#f1fa8c","red":"#ff5555"},
    }
    cols = st.columns(len(PRESETS) + 1)
    for i, (label, vals) in enumerate(PRESETS.items()):
        with cols[i]:
            if st.button(label, use_container_width=True, key=f"preset_{i}"):
                _appliquer_theme(vals); st.rerun()
    with cols[len(PRESETS)]:
        if st.button("🔄 Reset", use_container_width=True, key="btn_reset_theme"):
            _appliquer_theme(dict(THEME_DEFAULT))
            try:
                cfg = _cfg(); cfg.pop("theme_ftp", None); _save_cfg(cfg)
            except Exception: pass
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
                val = st.color_picker(label, value=th.get(key,"#ffffff"), key=f"th_{key}_v{ver}")
                st.session_state["theme_ftp"][key] = val

    with col_right:
        st.markdown("**Typographie & Mise en page**")
        font_opts = ["Arial,sans-serif","'Segoe UI',sans-serif","Georgia,serif","'Courier New',monospace","'Inter',sans-serif"]
        cur_font  = th.get("font","Arial,sans-serif")
        font_idx  = font_opts.index(cur_font) if cur_font in font_opts else 0
        font = st.selectbox("Police", font_opts, index=font_idx, key=f"th_font_v{ver}")
        st.session_state["theme_ftp"]["font"] = font
        fs  = st.slider("Taille du texte (px)", 11, 16, int(th.get("fs",13)), key=f"th_fs_v{ver}")
        st.session_state["theme_ftp"]["fs"] = str(fs)
        rad = st.slider("Rayon des cartes (px)", 0, 20, int(th.get("rad",8)), key=f"th_rad_v{ver}")
        st.session_state["theme_ftp"]["rad"] = str(rad)
        st.markdown("**Textes**")
        ptitle = st.text_input("Titre de la page", value=th.get("ptitle","Veille Technologique IA"), key=f"th_ptitle_v{ver}")
        st.session_state["theme_ftp"]["ptitle"] = ptitle

    t = st.session_state["theme_ftp"]
    st.markdown(
        f'<div style="margin-top:12px;padding:16px;background:{t["bg"]};border-radius:{t["rad"]}px;border:1px solid {t["brd"]};font-family:{t["font"]};">'
        f'<div style="font-size:18px;font-weight:bold;color:{t["blue"]};margin-bottom:10px;">{t["ptitle"]}</div>'
        f'<div style="font-size:12px;color:{t["sub"]};margin-bottom:12px;">Aperçu — {datetime.now().strftime("%d/%m/%Y")}</div>'
        f'<div style="background:{t["ov"]};border-radius:{t["rad"]}px;padding:10px 14px;margin-bottom:8px;">'
        f'<div style="font-size:13px;font-weight:600;color:{t["blue"]};">📂 Intelligence Artificielle</div>'
        f'<div style="font-size:12px;color:{t["sub"]};margin-top:6px;padding-left:12px;border-left:3px solid {t["blue"]};">'
        f'📅 08/04/2026 — 5 articles <span style="background:#a6e3a1;color:#1e1e2e;font-size:10px;padding:1px 6px;border-radius:6px;font-weight:700;">NOUVEAU</span></div>'
        f'</div>'
        f'<div style="padding:10px;background:linear-gradient(135deg,{t["bg"]},{t["surf"]});border-left:3px solid {t["yel"]};border-radius:6px;font-size:11px;color:{t["txt"]};">'
        f'— Synthèse · La convergence des modèles open-source s\'accélère [1]</div>'
        f'</div>', unsafe_allow_html=True)

    col_apply, col_save = st.columns(2)
    with col_apply:
        if st.button("🎨 Appliquer & republier sur FTP", type="primary", use_container_width=True, key="btn_apply_theme"):
            if srv.ftp_est_configure():
                with st.spinner("Regénération et upload FTP…"):
                    try:
                        h = _historique()
                        ok, msg = srv._publier_ftp_avec_historique(None, h, st.session_state["theme_ftp"])
                        st.success(f"✅ {msg}") if ok else st.error(msg)
                    except Exception as e:
                        st.error(f"Erreur : {e}")
            else:
                st.warning("FTP non configuré — allez dans Configuration.")
    with col_save:
        if st.button("💾 Sauvegarder le thème", use_container_width=True, key="btn_save_theme"):
            cfg = _cfg(); cfg["theme_ftp"] = json.dumps(st.session_state["theme_ftp"]); _save_cfg(cfg)
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
        if st.button("✨ S'abonner à 2,99€/mois", type="primary"): _goto("abonnement")
        return
    uid   = _user_id()
    prefs = {}
    if STORAGE_OK:
        try: prefs = storage.charger_veille_auto(uid) or {}
        except Exception: prefs = {}
    st.markdown('<div class="card card-accent">', unsafe_allow_html=True)
    st.markdown("#### Configurer votre veille automatique")
    sujets = st.text_area("Sujets (séparés par des virgules)", value=prefs.get("sujets",""),
                           placeholder="ex: intelligence artificielle, cybersécurité, LLM", height=80)
    st.markdown("#### Heure d'envoi")
    st.markdown('<div style="font-size:12px;color:var(--subtext);margin-bottom:12px;">La Réunion = UTC+4 · France = UTC+1 (hiver) / UTC+2 (été)</div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,1,2])
    with col1:
        heure_utc = st.selectbox("Heure (UTC)", list(range(24)), index=int(prefs.get("heure",4)),
                                  format_func=lambda h: f"{h:02d}h")
    with col2:
        opts = [0,15,30,45]; min_val = int(prefs.get("minute",0))
        minute_utc = st.selectbox("Minute", opts, index=opts.index(min_val) if min_val in opts else 0,
                                   format_func=lambda m: f"{m:02d}")
    with col3:
        h_reunion = (heure_utc+4)%24
        st.markdown(f'<div class="metric-box" style="margin-top:20px;"><span class="metric-val" style="font-size:20px;">{h_reunion:02d}h{minute_utc:02d}</span><span class="metric-lbl">Heure Réunion (UTC+4)</span></div>', unsafe_allow_html=True)
    actif = st.toggle("Activer la veille automatique", value=bool(prefs.get("actif",True)))
    st.markdown("</div>", unsafe_allow_html=True)
    if prefs.get("derniere_execution"):
        try:
            d = datetime.fromisoformat(str(prefs["derniere_execution"]).replace("Z","+00:00"))
            st.markdown(f'<div style="font-size:12px;color:var(--subtext);margin-top:8px;">Dernière exécution : {d.strftime("%d/%m/%Y à %H:%M")} UTC</div>', unsafe_allow_html=True)
        except Exception: pass
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    if st.button("💾 Enregistrer", type="primary"):
        ok_val, msg_val = _valider_texte(sujets, 500)
        if not ok_val:
            st.error(msg_val)
        elif not STORAGE_OK:
            st.error("Module storage indisponible.")
        else:
            try:
                ok = storage.sauvegarder_veille_auto(sujets.strip(), int(heure_utc), int(minute_utc), actif, uid)
                st.success(f"Veille {'activée' if actif else 'désactivée'} — envoi à {h_reunion:02d}h{minute_utc:02d} (Réunion)") if ok else st.error("Erreur Supabase.")
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
        '4. Vous n\'avez rien à faire — tout se passe sans connexion</div></div>',
        unsafe_allow_html=True)

# ============================================================
# PAGE ABONNEMENT
# ============================================================
def page_abonnement():
    st.markdown("# ✨ Abonnement"); st.markdown("---")
    if _est_abonne():
        st.markdown(
            '<div class="card card-green" style="padding:24px;text-align:center;">'
            '<div style="font-size:32px;margin-bottom:8px;">✅</div>'
            '<div style="font-size:18px;font-weight:600;color:var(--green);margin-bottom:8px;">Abonnement actif</div>'
            '<div style="font-size:13px;color:var(--subtext);">Recherches illimitées + veille email quotidienne.</div>'
            '</div>', unsafe_allow_html=True)
        st.info("Pour annuler, contactez support@veille-ia.fr")
    else:
        col_l, col_c, col_r = st.columns([1,1.5,1])
        with col_c:
            stripe_url = os.getenv("STRIPE_PAYMENT_LINK","")
            st.markdown(
                '<div class="abonnement-box">'
                '<div style="font-size:13px;color:var(--mauve);font-weight:600;letter-spacing:2px;text-transform:uppercase;margin-bottom:16px;">Veille IA Premium</div>'
                '<div style="font-size:48px;font-weight:700;">2,99€</div>'
                '<div style="font-size:14px;color:var(--subtext);margin-bottom:24px;">par mois · sans engagement</div>'
                '<div style="text-align:left;margin-bottom:24px;font-size:13px;line-height:2;">'
                '✔ Recherches illimitées<br>✔ Veille automatique par email<br>'
                '✔ Historique complet<br>✔ Résumés IA par article<br>✔ Comparaison entre sessions</div></div>',
                unsafe_allow_html=True)
            if stripe_url:
                st.markdown(f'<a href="{stripe_url}" target="_blank" style="display:block;text-align:center;background:var(--mauve);color:#1e1e2e;font-weight:700;font-size:15px;padding:14px;border-radius:10px;text-decoration:none;">✨ S\'abonner — 2,99€/mois</a>', unsafe_allow_html=True)
            else:
                st.warning("Paiement Stripe disponible prochainement.")

# ============================================================
# PAGE VEILLE
# ============================================================
def page_veille():
    st.markdown("# 🔍 Nouvelle veille")
    st.markdown("### Recherche, scoring et publication"); st.markdown("---")

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
                    '</div>', unsafe_allow_html=True)
                if st.button("✨ S'abonner à 2,99€/mois", type="primary"): _goto("abonnement")
                return
            st.markdown(f'<div style="margin-bottom:16px;">{_badge(f"Compte gratuit · {reste} recherche(s) restante(s)","yellow")}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="margin-bottom:16px;">{_badge("✨ Abonné · Recherches illimitées","mauve")}</div>', unsafe_allow_html=True)

    col_form, col_log = st.columns([1,1], gap="large")
    with col_form:
        st.markdown('<div class="card card-accent">', unsafe_allow_html=True)
        sujet  = st.text_area("Sujets de recherche", placeholder="ex: cybersécurité IA, deepfake, LLM Europe", height=90, key="sujet_input")
        c1, c2 = st.columns(2)
        with c1: limite = st.number_input("Articles max à résumer", min_value=1, max_value=50, value=10, step=1)
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            btn_rechercher = st.button("🔍 Rechercher", use_container_width=True,
                                       disabled=st.session_state["en_cours"], type="primary", key="btn_rechercher")
        with c2:
            if st.button("🗑 Réinitialiser", use_container_width=True, key="btn_reset_veille"):
                st.session_state.update({"logs":[],"resultats":[],"recherche_terminee":False,"derniere_publication":None})
                st.rerun()

        if st.session_state["resultats"] and not st.session_state["en_cours"]:
            st.markdown("---")
            nb_r = len(st.session_state["resultats"])
            st.markdown(f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;"><span style="font-family:Space Mono;font-size:13px;">Résultats</span>{_badge(f"{nb_r} articles trouvés","green")}</div>', unsafe_allow_html=True)
            for r in st.session_state["resultats"][:8]:
                dom   = urlparse(r.get("href","")).netloc
                score = r.get("score",0)
                c     = "green" if score>=80 else "yellow" if score>=50 else "red"
                st.markdown(
                    f'<div class="card" style="padding:10px 14px;margin-bottom:6px;">'
                    f'<div style="font-size:13px;font-weight:500;margin-bottom:3px;">{r.get("title","")[:72]}…</div>'
                    f'<div style="display:flex;gap:8px;"><span style="font-size:11px;color:var(--subtext)">{dom}</span>{_badge(f"score {score}",c)}</div></div>',
                    unsafe_allow_html=True)
            if len(st.session_state["resultats"]) > 8:
                st.caption(f"… et {len(st.session_state['resultats'])-8} autres articles")

    with col_log:
        if st.session_state["en_cours"]:
            sujet_affiche = st.session_state.get("sujet_courant","…")
            dernier_log   = st.session_state.get("dernier_log","Initialisation…")
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
            st.markdown('<div style="font-family:Space Mono;font-size:12px;color:var(--subtext);text-transform:uppercase;letter-spacing:1px;margin-bottom:10px;">— Journal</div>', unsafe_allow_html=True)
            log_html = "<br>".join(st.session_state["logs"][-40:] if st.session_state["logs"] else ["<span style='color:var(--subtext)'>En attente de lancement…</span>"])
            st.markdown(f'<div class="log-box">{log_html}</div>', unsafe_allow_html=True)

    if btn_rechercher and sujet.strip() and not st.session_state["en_cours"]:
        ok_val, msg_val = _valider_texte(sujet, 300)
        if not ok_val:
            st.error(msg_val); return
        if AUTH_OK and uid:
            ok_q, msg_q = auth.peut_rechercher(uid)
            if not ok_q: st.error(msg_q); return
        st.session_state.update({
            "en_cours":True,"resultats":[],"sujet_courant":sujet.strip(),
            "limite_courante":int(limite),"logs":[],"dernier_log":"Initialisation…",
            "recherche_terminee":False,"derniere_publication":None,
        })
        st.rerun()
    elif st.session_state["en_cours"] and st.session_state.get("sujet_courant"):
        sujet_run = st.session_state["sujet_courant"]
        try:
            resultats = srv.rechercher(sujet_run, callback_statut=_log)
            st.session_state["resultats"] = resultats
            _log(f"✅ {len(resultats)} résultats trouvés — prêt à publier")
            if AUTH_OK and uid and not abonne: auth.incrementer_quota(uid)
        except Exception as e:
            _log(f"❌ Erreur : {e}")
        st.session_state.update({"en_cours":False,"dernier_log":"","recherche_terminee":True})
        st.rerun()
    elif btn_rechercher and not sujet.strip():
        st.warning("Entrez au moins un sujet.")

    if st.session_state.get("recherche_terminee") and st.session_state["resultats"] and not st.session_state["en_cours"]:
        _render_panneau_publication(uid, abonne)

def _render_panneau_publication(uid, abonne):
    nb_r   = len(st.session_state["resultats"])
    limite = st.session_state.get("limite_courante",10)
    sujet  = st.session_state.get("sujet_courant","")

    st.markdown("---")
    st.markdown('<div style="font-family:Space Mono;font-size:14px;color:var(--green);margin-bottom:4px;">✅ Recherche terminée — choisissez où publier</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:12px;color:var(--subtext);margin-bottom:16px;">{nb_r} articles trouvés pour <strong style="color:var(--text)">{sujet}</strong>. Les résumés IA seront générés au moment de la publication.</div>', unsafe_allow_html=True)

    col_p1, col_p2 = st.columns(2)
    with col_p1:
        nb_articles = st.number_input("Articles à résumer et publier", min_value=1, max_value=min(nb_r,50), value=min(limite,nb_r), step=1, key="pub_nb_articles")
    with col_p2:
        mode_pub = st.selectbox("Mode WordPress", ["Mise à jour page","Créer un post"], key="pub_mode")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    col_b1, col_b2, col_b3 = st.columns(3)
    with col_b1: btn_wp   = st.button("🌐 Publier sur WordPress", use_container_width=True, key="btn_pub_wp",   disabled=st.session_state.get("en_cours_pub",False))
    with col_b2: btn_ftp  = st.button("📡 Publier sur FTP",       use_container_width=True, key="btn_pub_ftp",  disabled=st.session_state.get("en_cours_pub",False))
    with col_b3: btn_both = st.button("🚀 Publier partout",        use_container_width=True, key="btn_pub_both", disabled=st.session_state.get("en_cours_pub",False), type="primary")

    pub = st.session_state.get("derniere_publication")
    if pub:
        col_r1, col_r2 = st.columns(2)
        for col, ok_key, msg_key, label in [(col_r1,"ok_wp","msg_wp","WordPress"),(col_r2,"ok_ftp","msg_ftp","FTP / Page web")]:
            with col:
                ok  = pub.get(ok_key)
                msg = pub.get(msg_key,"")
                if ok is not None:
                    ic = "✅" if ok else "❌"; cl = "var(--green)" if ok else "var(--red)"
                    st.markdown(f'<div class="card" style="border-left:3px solid {cl};padding:12px 14px;margin-top:8px;"><div style="font-size:12px;font-weight:600;color:{cl};">{ic} {label}</div><div style="font-size:12px;color:var(--subtext);margin-top:4px;">{msg}</div></div>', unsafe_allow_html=True)

    cible_wp  = btn_wp  or btn_both
    cible_ftp = btn_ftp or btn_both

    if (cible_wp or cible_ftp) and not st.session_state.get("en_cours_pub",False):
        st.session_state["en_cours_pub"] = True
        pub_result = {"ok_wp":None,"msg_wp":"","ok_ftp":None,"msg_ftp":""}
        with st.spinner("Génération des résumés IA et publication…"):
            try:
                if mode_pub == "Mise à jour page" or cible_ftp:
                    res = srv.workflow_publier(sujet, st.session_state["resultats"], callback_statut=_log,
                                              limite=int(nb_articles), theme_ftp=st.session_state.get("theme_ftp"),
                                              publier_wp=bool(cible_wp), publier_ftp_flag=bool(cible_ftp))
                    if "wordpress" in res: pub_result["ok_wp"],pub_result["msg_wp"] = res["wordpress"]
                    if "ftp"       in res: pub_result["ok_ftp"],pub_result["msg_ftp"] = res["ftp"]
                elif mode_pub == "Créer un post" and cible_wp:
                    ok, msg = srv.workflow_creer_post(sujet, st.session_state["resultats"][:int(nb_articles)], callback_statut=_log)
                    pub_result["ok_wp"],pub_result["msg_wp"] = ok, msg
            except Exception as e:
                _log(f"❌ Erreur publication : {e}")
                pub_result["msg_wp"] = pub_result["msg_ftp"] = f"Erreur : {e}"
        st.session_state["derniere_publication"] = pub_result
        st.session_state["en_cours_pub"]         = False
        st.rerun()

# ============================================================
# PAGE HISTORIQUE
# ============================================================
def page_historique():
    st.markdown("# 📚 Historique des veilles"); st.markdown("---")
    h = _historique()
    sujets = [k for k in h if not k.startswith("__") and isinstance(h[k],list)]

    with st.expander("📥 Importer depuis un fichier veille-ia.html", expanded=not sujets):
        st.markdown('<div style="font-size:12px;color:var(--subtext);margin-bottom:12px;">Les fichiers générés par cette app contiennent un bloc de données caché pour un import fidèle.</div>', unsafe_allow_html=True)
        fichier = st.file_uploader("Fichier veille-ia.html", type=["html"], key="import_veille_html")
        if fichier is not None:
            try:
                contenu_html = fichier.read().decode("utf-8", errors="replace")
            except Exception as e:
                st.error(f"Lecture impossible : {e}")
            else:
                hist_imp = srv.extraire_historique_depuis_html(contenu_html)
                if hist_imp:
                    ns = len([k for k in hist_imp if not k.startswith("__")])
                    na = sum(len(s.get("articles",[])) for v in hist_imp.values() if isinstance(v,list) for s in v if isinstance(s,dict))
                    st.success(f"✅ {ns} sujet(s) · {na} article(s) détectés — prêt à fusionner.")
                    if st.button("Fusionner avec mon historique", type="primary", key="btn_merge_hist"):
                        merged = _fusionner_historique_import(h, hist_imp)
                        _sauvegarder_historique_complet(merged)
                        st.success("Historique mis à jour."); st.rerun()
                else:
                    st.warning("Aucune donnée reconnue dans ce fichier.")

    if not sujets:
        st.info("Aucun historique. Lancez une première veille ou importez un fichier HTML ci-dessus.")
        return

    st.markdown("---")
    col_g, col_d = st.columns([1,2], gap="large")
    with col_g:
        sujet_sel = st.selectbox("Sujet à afficher", sujets, key="hist_sujet_sel")
        sessions  = h.get(sujet_sel,[])
        st.markdown(f'<div class="metric-box" style="margin:12px 0;"><span class="metric-val">{len(sessions)}</span><span class="metric-lbl">Sessions</span></div>', unsafe_allow_html=True)
        st.markdown("---")
        st.markdown("#### Supprimer des sujets")
        sujets_a_supprimer = st.multiselect("Sélectionnez les sujets à supprimer", options=sujets, default=[], key="sujets_suppr", placeholder="Choisissez un ou plusieurs sujets…")
        if sujets_a_supprimer:
            st.markdown(f'<div style="font-size:12px;color:var(--red);margin:6px 0;">⚠️ {len(sujets_a_supprimer)} sujet(s) sélectionné(s)</div>', unsafe_allow_html=True)
            if st.button(f"🗑 Supprimer {len(sujets_a_supprimer)} sujet(s)", type="secondary", use_container_width=True, key="btn_suppr_sel"):
                for s in sujets_a_supprimer: _effacer_sujet(s)
                st.success(f"{len(sujets_a_supprimer)} sujet(s) supprimé(s)."); st.rerun()
        st.markdown("---")
        with st.expander("⚠️ Tout effacer"):
            if st.button("🗑 Effacer tout", type="secondary", use_container_width=True, key="btn_eff_tout"):
                _effacer_tout(); st.success("Historique effacé."); st.rerun()

    with col_d:
        for i, session in enumerate(sessions):
            if not isinstance(session, dict): continue
            date_s   = session.get("date","?")
            articles = session.get("articles",[])
            rg       = session.get("resume_global","")
            with st.expander(f"📅 {date_s} — {len(articles)} articles", expanded=(i==0)):
                if rg and not rg.startswith("Erreur"):
                    rg_affiche = rg[:1200] + ("…" if len(rg)>1200 else "")
                    st.markdown(f'<div class="card" style="border-left:3px solid var(--yellow);margin-bottom:16px;"><div style="font-size:12px;font-weight:600;color:var(--yellow);margin-bottom:8px;">SYNTHÈSE</div><div style="font-size:13px;line-height:1.7;">{rg_affiche}</div></div>', unsafe_allow_html=True)
                for a in sorted(articles, key=lambda x: x.get("score",0), reverse=True):
                    dom    = urlparse(a.get("href","")).netloc; score = a.get("score",0)
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
                        f'{pts_html}</div>', unsafe_allow_html=True)

# ============================================================
# PAGE COMPARAISON
# ============================================================
def page_comparaison():
    st.markdown("# 📊 Comparaison de sessions"); st.markdown("---")
    h = _historique()
    sujets = [k for k in h if not k.startswith("__") and isinstance(h[k],list)]
    if not sujets: st.info("Aucun historique."); return
    sujet_sel = st.selectbox("Sujet", sujets)
    sessions  = [s for s in h.get(sujet_sel,[]) if isinstance(s,dict)]
    if len(sessions) < 2: st.warning("Il faut au moins 2 sessions."); return
    dates = [s.get("date",f"Session {i+1}") for i,s in enumerate(sessions)]
    c1, c2 = st.columns(2)
    with c1: date_rec = st.selectbox("Session récente",    dates, index=0)
    with c2: date_anc = st.selectbox("Session précédente", dates, index=min(1,len(dates)-1))
    if date_rec == date_anc: st.warning("Choisissez deux sessions différentes."); return
    sess_rec = next((s for s in sessions if s.get("date")==date_rec), None)
    sess_anc = next((s for s in sessions if s.get("date")==date_anc), None)
    if not sess_rec or not sess_anc: st.error("Sessions introuvables."); return
    hrefs_anc = {a["href"] for a in sess_anc.get("articles",[]) if "href" in a}
    hrefs_rec = {a["href"] for a in sess_rec.get("articles",[]) if "href" in a}
    nouveaux  = hrefs_rec - hrefs_anc; disparus = hrefs_anc - hrefs_rec
    c1, c2, c3 = st.columns(3)
    for col, val, lbl, clr in [(c1,len(sess_rec.get("articles",[])),"Récents","blue"),(c2,len(nouveaux),"Nouveaux","green"),(c3,len(disparus),"Disparus","red")]:
        with col:
            st.markdown(f'<div class="metric-box"><span class="metric-val" style="color:var(--{clr})">{val}</span><span class="metric-lbl">{lbl}</span></div>', unsafe_allow_html=True)
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    if st.button("🧠 Générer l'analyse", type="primary"):
        with st.spinner("Analyse IA…"):
            try:
                analyse = srv.comparer_sessions(sujet_sel, sess_rec, sess_anc)
                st.markdown(f'<div class="card card-accent" style="margin-top:16px;"><div style="font-size:12px;font-weight:600;color:var(--mauve);margin-bottom:12px;">ANALYSE COMPARATIVE</div><div style="font-size:13px;line-height:1.8;white-space:pre-line">{analyse}</div></div>', unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Erreur : {e}")

# ============================================================
# PAGE CONFIG
# ============================================================
def page_config():
    st.markdown("# ⚙️ Configuration"); st.markdown("---")
    cfg = _cfg()
    ftp_host = cfg.get("ftp_host","")
    exemple_url = f"https://{ftp_host}/veille-ia.html" if ftp_host else "https://monsite.com/veille-ia.html"

    tab_wp, tab_ftp, tab_theme, tab_integration = st.tabs(
        ["🌐 WordPress","📡 FTP","🎨 Thème & Affichage","🔗 Intégration"])

    with tab_wp:
        st.markdown("#### Connexion WordPress")
        wp_base = st.text_input("URL du site", value=cfg.get("wp_base",""), placeholder="https://monsite.com")
        c1, c2  = st.columns(2)
        with c1: wp_user = st.text_input("Identifiant",      value=cfg.get("wp_user",""))
        with c2: wp_pwd  = st.text_input("Mot de passe app", value=cfg.get("wp_password",""), type="password")
        cs, ct  = st.columns(2)
        with cs:
            if st.button("💾 Sauvegarder", use_container_width=True, key="btn_save_wp"):
                cfg.update({"wp_base":wp_base,"wp_user":wp_user,"wp_password":wp_pwd}); _save_cfg(cfg); st.success("Sauvegardé !")
        with ct:
            if st.button("🔌 Tester WP", use_container_width=True, key="btn_test_wp"):
                ok, msg = srv.tester_connexion_wp(wp_base, wp_user, wp_pwd)
                if ok: st.success(msg)
                else:  st.error(msg)

    with tab_ftp:
        st.markdown("#### Connexion FTP")
        ftp_host_input = st.text_input("Hôte FTP", value=cfg.get("ftp_host",""))
        c1, c2         = st.columns(2)
        with c1: ftp_user = st.text_input("Utilisateur FTP", value=cfg.get("ftp_user",""))
        with c2: ftp_pwd  = st.text_input("Mot de passe FTP",value=cfg.get("ftp_password",""), type="password")
        ftp_path = st.text_input("Chemin distant", value=cfg.get("ftp_path","/htdocs/veille-ia.html"))
        cs, ct   = st.columns(2)
        with cs:
            if st.button("💾 Sauvegarder FTP", use_container_width=True, key="btn_save_ftp"):
                cfg.update({"ftp_host":ftp_host_input,"ftp_user":ftp_user,"ftp_password":ftp_pwd,"ftp_path":ftp_path}); _save_cfg(cfg); st.success("Sauvegardé !")
        with ct:
            if st.button("🔌 Tester FTP", use_container_width=True, key="btn_test_ftp"):
                ok, msg = srv.tester_connexion_ftp(ftp_host_input, ftp_user, ftp_pwd)
                if ok: st.success(msg)
                else:  st.error(msg)

    with tab_theme:
        _render_theme_editor()

    with tab_integration:
        st.markdown("#### 🔗 Intégrer la veille sur une autre page")
        st.markdown('<div style="font-size:13px;color:var(--subtext);margin-bottom:20px;">Une fois votre veille publiée sur FTP, copiez l\'un des snippets ci-dessous.</div>', unsafe_allow_html=True)
        url_veille = st.text_input("URL publique de votre veille-ia.html", value=exemple_url, placeholder="https://monsite.com/veille-ia.html", key="integration_url")
        st.markdown("---")
        st.markdown("#### ⚙️ Options d'affichage")
        col_pos, col_larg = st.columns(2)
        with col_pos:
            position = st.selectbox("Position", ["Centré (milieu)","Gauche","Droite","Pleine largeur"], key="iframe_position")
        with col_larg:
            largeur_px = st.number_input("Largeur (px) — ignorée si Pleine largeur", min_value=300, max_value=2000, value=900, step=50, key="iframe_largeur")
        hauteur_px = st.number_input("Hauteur de l'iframe (px)", min_value=400, max_value=5000, value=1800, step=100, key="iframe_hauteur")
        if position == "Pleine largeur":
            width_css = "100%"; wrapper_css = ""
        elif position == "Centré (milieu)":
            width_css = f"{largeur_px}px"; wrapper_css = "text-align:center;"
        elif position == "Gauche":
            width_css = f"{largeur_px}px"; wrapper_css = "text-align:left;"
        else:
            width_css = f"{largeur_px}px"; wrapper_css = "text-align:right;"
        st.markdown("---")
        st.markdown('<div style="font-family:Space Mono;font-size:12px;color:var(--blue);margin-bottom:6px;">▶ Méthode 1 — iframe auto-hauteur (recommandée)</div>', unsafe_allow_html=True)
        st.code(f"""<div style="{wrapper_css}">
<div id="veille-container"></div>
</div>
<script>
var url = "{url_veille}?v=" + Date.now();
document.getElementById("veille-container").innerHTML =
  '<iframe src="' + url + '" style="width:{width_css};border:none;" ' +
  'onload="this.style.height=this.contentDocument.body.scrollHeight+\\'px\\'"></iframe>';
</script>""", language="html")
        st.markdown('<div style="font-family:Space Mono;font-size:12px;color:var(--blue);margin-bottom:6px;margin-top:16px;">▶ Méthode 2 — iframe hauteur fixe</div>', unsafe_allow_html=True)
        st.code(f"""<div style="{wrapper_css}">
<iframe src="{url_veille}?v=TIMESTAMP"
  style="width:{width_css}; height:{hauteur_px}px; border:none;" loading="lazy">
</iframe>
</div>""", language="html")
        st.markdown('<div style="font-family:Space Mono;font-size:12px;color:var(--blue);margin-bottom:6px;margin-top:16px;">▶ Méthode 3 — lien direct</div>', unsafe_allow_html=True)
        st.code(f'<a href="{url_veille}" target="_blank" style="display:inline-block;padding:10px 20px;background:#89b4fa;color:#1e1e2e;border-radius:8px;font-weight:bold;text-decoration:none;">📡 Voir la veille technologique</a>', language="html")
        st.markdown("---")
        st.markdown('<div class="card card-accent" style="padding:14px 16px;"><div style="font-size:13px;font-weight:600;color:var(--blue);margin-bottom:8px;">📝 Note WordPress</div><div style="font-size:12px;color:var(--subtext);line-height:1.8;">WordPress filtre le HTML par défaut. Utilisez l\'éditeur <strong style="color:var(--text)">HTML / Code source</strong>, le plugin <strong style="color:var(--text)">WPCode</strong>, ou un bloc <strong style="color:var(--text)">HTML personnalisé</strong>.</div></div>', unsafe_allow_html=True)

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        mode_s = "Supabase ☁️" if (STORAGE_OK and getattr(storage,"SUPABASE_OK",False)) else "Fichier local 💾"
        st.markdown(f'<div class="card"><div style="font-size:11px;color:var(--subtext)">Stockage</div><div style="font-size:13px;font-weight:500;margin-top:4px">{mode_s}</div></div>', unsafe_allow_html=True)
    with c2:
        h = _historique()
        nb_s = sum(1 for k in h if not k.startswith("__"))
        nb_a = sum(len(s.get("articles",[])) for ss in h.values() if isinstance(ss,list) for s in ss if isinstance(s,dict))
        st.markdown(f'<div class="card"><div style="font-size:12px;color:var(--subtext)">Historique</div><div style="font-size:12px;margin-top:4px">{nb_s} sujets · {nb_a} articles</div></div>', unsafe_allow_html=True)

# ============================================================
# PAGE CONDITIONS
# ============================================================
def page_conditions():
    st.markdown("# 📄 Conditions d'utilisation"); st.markdown("---")
    st.markdown("""
En utilisant Veille IA, vous acceptez notamment que :

- Le service collecte les données nécessaires au fonctionnement (compte, configuration, historique).
- Les contenus analysés peuvent être traités par des services tiers (IA, email, hébergement).
- Vous restez responsable des publications effectuées vers WordPress/FTP.
- Le service est fourni "en l'état" et peut évoluer.
- Vous pouvez demander la suppression de vos données selon la politique en vigueur.
    """)
    uid = _user_id()
    if _conditions_acceptees():
        st.success("Conditions déjà acceptées.")
        if st.button("Retour", type="primary"): _goto("veille")
        return
    cgu_ok = st.checkbox("J'ai lu et j'accepte les Conditions d'utilisation.")
    if st.button("✅ Accepter et continuer", type="primary", disabled=not cgu_ok):
        if not AUTH_OK or not uid: st.error("Session invalide. Reconnectez-vous."); return
        if hasattr(auth, "accepter_conditions"):
            res = auth.accepter_conditions(uid)
            if res.get("ok"):
                st.session_state["profil"] = auth.get_profil(uid)
                st.success("Conditions enregistrées."); _goto("veille")
            else:
                st.error(res.get("message","Erreur lors de l'enregistrement."))
        else:
            _goto("veille")

# ============================================================
# PAGE CONFORMITÉ RGPD
# ============================================================
def page_conformite():
    st.markdown("# 🛡️ Conformité & RGPD"); st.markdown("---")
    st.info("Cette page est un modèle à personnaliser avec vos informations légales définitives.")
    sections = [
        ("1) Responsable du traitement", "- **Editeur** : lucas rajany\n- **Contact** : lucas.rajanysio@gmail.com\n- **DPO** : À COMPLÉTER"),
        ("2) Données collectées", "- Données de compte : email, identifiant.\n- Configuration : préférences, intégrations WordPress/FTP.\n- Contenu : sujets, résultats, historique.\n- Technique : journaux de fonctionnement."),
        ("3) Finalités du traitement", "- Fournir le service de veille.\n- Générer des résumés et synthèses IA.\n- Publier sur les intégrations choisies.\n- Envoyer des emails automatiques si activé."),
        ("4) Base légale", "- **Consentement** : inscription et acceptation des CGU.\n- **Intérêt légitime** : sécurité, prévention des abus."),
        ("5) Durée de conservation", "- Compte : pendant la durée d'utilisation.\n- Historique : jusqu'à suppression par l'utilisateur.\n- Logs : durée limitée pour sécurité et diagnostic."),
        ("6) Sous-traitants", "- Hébergement / BDD : Supabase.\n- IA : Groq.\n- Email : Gmail SMTP.\n- Paiement : Stripe."),
        ("7) Droits des personnes", "Accès, rectification, effacement, limitation, opposition, portabilité via : lucas.rajanysio@gmail.com"),
        ("8) Sécurité", "- Contrôle d'accès aux comptes.\n- Stockage segmenté par utilisateur.\n- Mesures techniques et organisationnelles."),
    ]
    for titre, contenu in sections:
        with st.expander(titre):
            st.markdown(contenu)
    st.markdown("---")

# ============================================================
# ROUTING PRINCIPAL
# ============================================================
user = st.session_state.get("user")

if user:
    _activer_storage(user.id)
    try:
        cfg_saved = _cfg()
        if "theme_ftp" in cfg_saved and isinstance(cfg_saved["theme_ftp"],str):
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
        {
            "veille":      page_veille,
            "historique":  page_historique,
            "comparaison": page_comparaison,
            "auto":        page_auto,
            "config":      page_config,
            "abonnement":  page_abonnement,
            "conditions":  page_conditions,
            "conformite":  page_conformite,
        }.get(page, page_veille)()

# ============================================================
# CHATBOT — toujours affiché en dernier (widget flottant)
# ============================================================
render_chatbot()
