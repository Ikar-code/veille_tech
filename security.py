"""
Helpers de securite pour valider les entrees utilisateur.
"""

import re

# Detection simple des motifs SQL frequents en attaque.
SQLI_PATTERNS = [
    r"(--|/\*|\*/|;)",
    r"\b(or|and)\b\s+\d+\s*=\s*\d+",
    r"\bunion\b\s+\bselect\b",
    r"\bdrop\b\s+\btable\b",
    r"\binsert\b\s+\binto\b",
    r"\bdelete\b\s+\bfrom\b",
    r"\bupdate\b\s+\w+\s+\bset\b",
]


def contient_pattern_suspect(valeur: str) -> bool:
    if not valeur:
        return False
    txt = valeur.lower().strip()
    for pattern in SQLI_PATTERNS:
        if re.search(pattern, txt):
            return True
    return False


def valider_email(email: str) -> tuple:
    if not email or "@" not in email:
        return False, "Email invalide."
    if len(email) > 254:
        return False, "Email trop long."
    if contient_pattern_suspect(email):
        return False, "Entree non autorisee."
    return True, ""


def valider_texte_recherche(texte: str, longueur_max: int = 300) -> tuple:
    if not texte or not texte.strip():
        return False, "Entrez au moins un sujet."
    if len(texte) > longueur_max:
        return False, f"Texte trop long (max {longueur_max} caracteres)."
    if contient_pattern_suspect(texte):
        return False, "Entree non autorisee."
    return True, ""
