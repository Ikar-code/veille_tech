# ============================================================
# CHATBOT.PY — Widget support Groq (LLaMA)
# Répond aux questions sur la plateforme Veille IA
# ============================================================

import requests
import os

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

SYSTEM_PROMPT = """Tu es l'assistant support de la plateforme "Veille IA", un outil de veille technologique automatisée créé par Lucas Rajany.

Tu réponds uniquement aux questions liées à la plateforme. Tu es concis, amical, et tu répondas en français.

FONCTIONNALITÉS DE LA PLATEFORME :
- Nouvelle veille : recherche automatique via DuckDuckGo + flux RSS, scoring des articles, résumés IA avec Groq (LLaMA)
- Historique : consultation et suppression des veilles passées
- Comparaison : analyse des évolutions entre deux sessions
- Automatisation : veille quotidienne par email (abonnés uniquement)
- Configuration : connexion WordPress (API REST) et FTP pour publier les résultats
- Thème : personnalisation de la page veille-ia.html publiée sur le site

ABONNEMENT :
- Offre gratuite : 1 recherche offerte
- Abonnement Premium : 2,99€/mois — recherches illimitées, veille auto par email
- Paiement via Stripe

PROBLÈMES FRÉQUENTS :
- "Traitement en cours bloqué" → normal pendant la génération des résumés IA, patienter 30-60s selon le nombre d'articles
- "WordPress rouge dans la sidebar" → vérifier l'URL du site et le mot de passe d'application dans Configuration
- "FTP non configuré" → renseigner hôte, utilisateur, mot de passe et chemin dans Configuration > FTP
- "Erreur Groq 429" → limite de taux atteinte, réessayer dans quelques secondes
- "Aucun résultat" → essayer des sujets plus précis ou en anglais
- "Page veille-ia.html vide" → relancer une veille et republier sur FTP

CONTACT : lucas.rajanysio@gmail.com

Si une question est hors sujet (non liée à la plateforme), réponds poliment que tu ne peux répondre qu'aux questions liées à Veille IA.
Réponds toujours en moins de 3 phrases sauf si une explication détaillée est vraiment nécessaire."""

QUESTIONS_PREDEFINIES = [
    "Comment lancer une veille ?",
    "Pourquoi ça reste bloqué ?",
    "Comment configurer le FTP ?",
    "C'est quoi l'abonnement ?",
    "Comment publier sur WordPress ?",
    "Comment personnaliser le thème ?",
    "Pourquoi je n'ai pas de résultats ?",
    "Comment fonctionne la veille auto ?",
]

def repondre(historique_messages: list) -> str:
    if not GROQ_API_KEY:
        return "⚠️ Clé API Groq manquante. Configurez la variable d'environnement GROQ_API_KEY."
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + historique_messages
    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={"model": "llama-3.1-8b-instant", "max_tokens": 400, "temperature": 0.5, "messages": messages},
            timeout=20,
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"].strip()
        elif resp.status_code == 429:
            return "⏳ Trop de requêtes en ce moment, réessaie dans quelques secondes."
        else:
            return f"❌ Erreur Groq ({resp.status_code}). Réessaie plus tard."
    except requests.exceptions.Timeout:
        return "⏳ La réponse met trop de temps, réessaie."
    except Exception as e:
        return f"❌ Erreur : {e}"
