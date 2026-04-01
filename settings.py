"""
Parametres centraux de l'application.
"""

# Recherche / publication
MAX_ARTICLES_PAR_RECHERCHE = 50
SCORE_MIN_PRIMAIRE = 50
SCORE_MIN_SECONDAIRE = 35

# Reseau
TIMEOUT_HTTP_COURT = 10
TIMEOUT_HTTP_STANDARD = 15
TIMEOUT_HTTP_LONG = 30

# Delais entre appels externes (anti-rate-limit)
DELAI_RESUME_SECONDES = 4
DELAI_SYNTHESE_SECONDES = 10
