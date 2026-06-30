# Veille IA

> **Veille IA** est une plateforme automatisée de veille technologique utilisant l'intelligence artificielle pour rechercher, analyser, résumer et publier des informations sur les nouvelles technologies.

Le projet a pour objectif de supprimer le travail manuel de veille en construisant un pipeline capable de collecter des informations depuis plusieurs sources, d'évaluer leur pertinence, de générer des synthèses et de produire automatiquement un contenu exploitable.

## Vision

Veille IA n'est pas simplement un agrégateur d'articles.

Le système fonctionne comme un pipeline automatisé combinant recherche, analyse et génération de contenu :

* collecte automatique d'informations ;
* filtrage des contenus pertinents ;
* analyse par modèles IA ;
* génération de résumés structurés ;
* publication automatisée.

L'objectif est de créer un assistant capable de transformer une recherche complexe en une veille claire et organisée.

---

# Fonctionnalités

## Recherche multi-sources

Le système récupère automatiquement des informations depuis différentes sources :

* recherche web ;
* flux RSS spécialisés ;
* sources technologiques ;
* contenus liés à l'intelligence artificielle.

Les résultats sont ensuite traités pour éviter les doublons et conserver uniquement les informations pertinentes.

## Analyse et filtrage intelligent

Chaque contenu est analysé selon plusieurs critères :

* pertinence du sujet ;
* qualité de la source ;
* fraîcheur de l'information ;
* cohérence avec les thèmes suivis.

## Résumés générés par IA

Les articles collectés sont transformés en synthèses :

* résumé automatique ;
* points importants ;
* informations clés ;
* regroupement par thématique.

## Publication automatisée

Le système peut générer automatiquement une sortie exploitable :

* page web ;
* article HTML ;
* contenu structuré ;
* historique des veilles.

## Historique et suivi

Les recherches peuvent être sauvegardées afin de :

* comparer différentes sessions ;
* retrouver d'anciennes analyses ;
* suivre l'évolution d'un sujet.

---

# Architecture

```text
Sources Web / RSS
        │
        ▼
Agent Recherche
        │
        ▼
Agent Analyse
        │
        ▼
Agent Résumé IA
        │
        ▼
Stockage
        │
        ▼
Publication
```

---

# Agents IA

## Agent Recherche

Collecte les informations depuis les sources configurées.

Responsabilités :

* récupération des données ;
* extraction des contenus ;
* préparation des sujets.

## Agent Vérification

Analyse les informations récupérées.

Responsabilités :

* cohérence des données ;
* vérification des éléments importants ;
* réduction des erreurs.

## Agent Rédaction

Transforme les informations validées en contenu structuré.

Responsabilités :

* génération de résumé ;
* organisation du contenu ;
* adaptation du format.

## Agent Qualité

Contrôle le résultat final avant publication.

Responsabilités :

* analyse de la qualité ;
* validation du contenu ;
* détection des problèmes.

---

# Technologies utilisées

## Backend

* Python
* APIs IA
* Automatisation

## Intelligence artificielle

* Groq API
* Modèles LLM
* Agents IA spécialisés

## Données

* Recherche web
* Flux RSS
* Scraping

## Stockage

* Supabase

## Automatisation

* GitHub Actions

---

# Objectifs futurs

* Ajout de nouvelles sources personnalisables ;
* Analyse de tendances ;
* Détection automatique de sujets émergents ;
* Notifications automatiques ;
* Dashboard analytique ;
* Amélioration des agents IA.

---

# Installation

```bash
git clone https://github.com/ikar-code/veille-tech.git

cd veille-ia

npm install
```

Configurer les variables d'environnement nécessaires :

```env
API_KEY=
SUPABASE_URL=
SUPABASE_KEY=
```

Lancer le projet :

```bash
npm run dev
```

---

# Avertissement

Veille IA est un projet personnel de recherche et développement autour de l'automatisation et de l'intelligence artificielle.

Les résultats générés automatiquement doivent toujours être vérifiés avant utilisation dans un contexte critique.

---

Développé par **Lucas Rajany**
