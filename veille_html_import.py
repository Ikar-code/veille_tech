"""
Import d'historique depuis veille-ia.html.

- Fichiers récents : commentaire <!--VEILLE_DATA_B64:...:END_VEILLE_DATA_B64-->
- Anciens fichiers : HTML seul (sans payload) → reconstruction par analyse du DOM texte
"""

from __future__ import annotations

import base64
import html as html_lib
import json
import re
from typing import Any

MARKER_B64_START = "<!--VEILLE_DATA_B64:"
MARKER_B64_END = ":END_VEILLE_DATA_B64-->"
MARKER_JSON_START = "<!--VEILLE_DATA:"
MARKER_JSON_END = ":END_VEILLE_DATA-->"


def format_embedded_historique(historique: dict[str, Any]) -> str:
    """Commentaire HTML à coller avant </body> pour import fidèle."""
    if not historique:
        return ""
    try:
        payload = base64.b64encode(
            json.dumps(historique, ensure_ascii=False).encode("utf-8")
        ).decode("ascii")
        return f"\n{MARKER_B64_START}{payload}{MARKER_B64_END}\n"
    except Exception:
        return ""


def _strip_tags(s: str) -> str:
    t = re.sub(r"<[^>]+>", " ", s)
    t = re.sub(r"\s+", " ", t).strip()
    return html_lib.unescape(t)


def _parse_embedded_b64(html: str) -> dict[str, Any] | None:
    i = html.find(MARKER_B64_START)
    if i == -1:
        return None
    j = html.find(MARKER_B64_END, i)
    if j == -1:
        return None
    b64 = html[i + len(MARKER_B64_START) : j].strip()
    try:
        raw = base64.b64decode(b64.encode("ascii")).decode("utf-8")
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except (ValueError, json.JSONDecodeError):
        return None


def _parse_embedded_json_legacy(html: str) -> dict[str, Any] | None:
    i = html.find(MARKER_JSON_START)
    if i == -1:
        return None
    rest = html[i + len(MARKER_JSON_START) :]
    j = rest.find(MARKER_JSON_END)
    if j == -1:
        return None
    js = rest[:j]
    try:
        data = json.loads(js)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


def _parse_table_rows(table_html: str) -> list[dict[str, Any]]:
    articles: list[dict[str, Any]] = []
    for row_m in re.finditer(r"<tr\b[^>]*>([\s\S]*?)</tr>", table_html, re.IGNORECASE):
        row = row_m.group(1)
        if "<th" in row.lower():
            continue
        if re.search(r"Langue|Titre\s*&amp;\s*Résumé", row, re.I):
            continue
        title_m = re.search(r"<strong>([\s\S]*?)</strong>", row, re.I)
        if not title_m:
            continue
        title = _strip_tags(title_m.group(1))
        if not title:
            continue
        href_m = re.search(
            r'<a\s+[^>]*href="([^"]+)"[^>]*>\s*ouvrir\s*</a>',
            row,
            re.I,
        )
        href = href_m.group(1).strip() if href_m else ""
        bullets: list[str] = []
        for li_m in re.finditer(r"<li\b[^>]*>([\s\S]*?)</li>", row, re.I):
            txt = _strip_tags(li_m.group(1))
            if txt:
                bullets.append(txt)
        articles.append(
            {
                "title": title,
                "href": href,
                "score": 0,
                "resume_ollama": bullets if bullets else ["Résumé importé depuis HTML."],
                "date_recherche": "",
            }
        )
    return articles


def _extract_resume_after_table(segment_after_table: str) -> str:
    """Texte de synthèse à partir du bloc HTML après </table>."""
    if "Synthèse" not in segment_after_table:
        return ""
    # Garde le bloc après la première occurrence de Synthèse
    idx = segment_after_table.find("Synthèse")
    chunk = segment_after_table[idx:]
    # Retire le titre type "Synthèse — ... (N articles)"
    txt = _strip_tags(chunk)
    return txt[:80000] if txt else ""


def parse_legacy_html_export(html: str) -> dict[str, Any]:
    """
    Reconstruit un dict historique depuis un export HTML sans payload JSON.
    """
    out: dict[str, list] = {}

    subj_blocks = list(
        re.finditer(
            r'font-size:\s*20px[\s\S]*?font-weight:\s*bold[\s\S]*?>\s*([^<]+?)\s*</div>',
            html,
            re.I,
        )
    )
    if not subj_blocks:
        # Un seul sujet possible sans en-tête explicite
        subj_blocks = [None]

    for bi, subj_m in enumerate(subj_blocks):
        if subj_m:
            subject = _strip_tags(subj_m.group(1)).lower()
            start = subj_m.end()
            end = subj_blocks[bi + 1].start() if bi + 1 < len(subj_blocks) else len(html)
            block = html[start:end]
        else:
            subject = "import veille"
            block = html

        dates = list(re.finditer(r"Recherche\s+du\s+(\d{2}/\d{2}/\d{4})", block, re.I))
        if not dates:
            continue

        sessions: list[dict[str, Any]] = []
        for di, dm in enumerate(dates):
            d = dm.group(1)
            seg_start = dm.start()
            seg_end = dates[di + 1].start() if di + 1 < len(dates) else len(block)
            segment = block[seg_start:seg_end]

            tm = re.search(r"<table\b[^>]*>([\s\S]*?)</table>", segment, re.I)
            if not tm:
                continue
            table_html = tm.group(0)
            articles = _parse_table_rows(table_html)
            after = segment.split("</table>", 1)[1] if "</table>" in segment else ""
            resume_global = _extract_resume_after_table(after)

            for a in articles:
                a["date_recherche"] = d

            sessions.append(
                {
                    "date": d,
                    "articles": articles,
                    "resume_global": resume_global,
                }
            )

        if sessions:
            # Clé normalisée comme dans serveur.workflow_publier
            key = subject.strip().lower()
            out[key] = sessions

    return out


def parse_veille_html_file(html: str) -> tuple[dict[str, Any] | None, str]:
    """
    Retourne (historique_dict, message).
    Si échec, (None, raison).
    """
    html = html.strip()
    if not html:
        return None, "Fichier vide."

    data = _parse_embedded_b64(html)
    if data is not None:
        return data, "Données embarquées (B64) détectées."

    data = _parse_embedded_json_legacy(html)
    if data is not None:
        return data, "Données embarquées (JSON) détectées."

    legacy = parse_legacy_html_export(html)
    if not legacy:
        return (
            None,
            "Impossible de lire cet HTML. "
            "Réessayez avec un fichier généré par l’app, ou republiez sur FTP "
            "(les nouveaux exports incluent les données pour l’import).",
        )

    return legacy, f"Import depuis HTML ({len(legacy)} sujet(s)) — reconstruction automatique."
