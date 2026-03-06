"""
test_copy_compliance.py — U5 : Conformité copy (mots interdits)
================================================================

Objectif : détecter automatiquement toute régression où un développeur
réintroduirait des formulations interdites dans le code ou les textes UI.

R1 du Risk Register (Score 12 — CRITIQUE) :
  "L'UI ou le marketing laisse entendre que l'app 'prévoit' les numéros gagnants."

R11 du Risk Register (Score 8) :
  "Un dev réintroduit 'gagnant', 'prédire' dans le copy."

Ce test scan les fichiers du projet à la recherche des phrases interdites
définies dans le Copy Compliance Lint (Copy_Compliance_Lint_EuroMillion.pdf).

GATE PROD : Ce test est BLOQUANT. Zéro occurrence autorisée (hors whitelist).
"""

import re
import pytest
from pathlib import Path

# ─────────────────────────────────────────────
# Racine du projet
# ─────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent.parent


# ─────────────────────────────────────────────
# Liste des phrases interdites (Copy Compliance Lint)
# Source : Copy_Compliance_Lint_EuroMillion.pdf
# ─────────────────────────────────────────────
FORBIDDEN_PHRASES = [
    # Catégorie A — Promesse de gain
    r"augmente\w* (vos|tes|les|mes) chances",
    r"plus de chances de gagner",
    r"maximis\w* (vos|tes) chances",
    r"garantie de gain",
    r"gagner à coup sûr",
    r"assuré[e]? de gagner",
    r"stratégie sûre",
    r"méthode (sûre|infaillible)",
    r"solution infaillible",
    r"secret pour gagner",
    r"(astuce|technique|hack|truc) pour gagner",

    # Catégorie B — Prédire les gagnants
    r"prédire les (numéros|chiffres) gagnants",
    r"prédire les résultats",
    r"prédit les numéros gagnants",
    r"numéros gagnants",
    r"chiffres gagnants",
    r"numéros (sûrs|garantis)",
    r"bons numéros",
    r"les prochains numéros",
    r"les numéros de ce soir",
    r"combinaison gagnante",
    r"grille gagnante",
    r"gagnant [àa] l.euromillions",
    r"gagner l.euromillions",
    r"gagner euromillions",

    # Catégorie C — Probabilité de gagner (hors contexte whitelist)
    # Note : ces patterns sont vérifiés séparément (whitelist_check)

    # Catégorie D — Formulations IA trompeuses
    r"ia gagnante",
    r"ia qui (gagne|bat)",
    r"bat le hasard",
    r"surpasse le hasard",
    r"déjoue le hasard",
    r"prédiction (fiable|certaine|garantie)",
    r"précision de prédiction",

    # Catégorie E — Incitation forte
    r"\bmise tout\b",
    r"\bparie tout\b",
    r"\bjoue tout\b",
    r"\ball[- ]in\b",
]

# ─────────────────────────────────────────────
# Whitelist — phrases autorisées (disclaimers)
# Ces patterns matchent des phrases qui CONTIENNENT des mots interdits
# mais dans un contexte de mise en garde (autorisé).
# ─────────────────────────────────────────────
WHITELIST_PATTERNS = [
    r"aucune garantie de gain",
    r"ne garantit pas de gain",
    r"n.offre aucune garantie de gain",
    r"n.augmente pas la probabilité de gagner",
    r"ne change pas la probabilité de gagner",
    r"ne rend pas le tirage prédictible",
    r"jeu de hasard",
    r"résultats aléatoires et indépendants",
    r"à titre (informatif|pédagogique)",
    r"outil expérimental",
    r"score anti-partage",
    r"réduire le risque de partager un gain",
    r"ne (change|modifie|augmente|améliore) pas la probabilité",
    r"n.augmente pas la (probabilité|chance)",
    r"numéros gagnants.*ne",           # ex: "Ne prédit pas les numéros gagnants"
    r"ne.*numéros gagnants",
    r"pas.*numéros gagnants",
    r"ne prédit pas",
    r"n.essaie pas de prédire",
    r"partager un gain si vous gagnez",
    r"risque de partager",
]

# ─────────────────────────────────────────────
# Fichiers à scanner
# ─────────────────────────────────────────────
def get_files_to_scan() -> list[Path]:
    """
    Retourne la liste des fichiers Python et JS/TS à scanner.
    Exclut les dossiers de dépendances et de build.
    """
    excluded_dirs = {
        "node_modules", ".venv", "venv", "dist", "build",
        "__pycache__", ".git", ".pytest_cache",
    }
    extensions = {".py", ".ts", ".tsx", ".js", ".jsx", ".md"}
    files = []

    for path in PROJECT_ROOT.rglob("*"):
        # Exclure les dossiers non pertinents
        if any(excl in path.parts for excl in excluded_dirs):
            continue
        # Exclure ce fichier de test lui-même (il contient les phrases pour les tester)
        if path.name == "test_copy_compliance.py":
            continue
        if path.suffix in extensions and path.is_file():
            files.append(path)

    return files


def is_whitelisted(line: str) -> bool:
    """Retourne True si la ligne est couverte par la whitelist."""
    line_lower = line.lower()
    return any(
        re.search(pat, line_lower, re.IGNORECASE)
        for pat in WHITELIST_PATTERNS
    )


def scan_file(filepath: Path) -> list[dict]:
    """
    Scanne un fichier et retourne les occurrences de phrases interdites.
    Retourne : [{"file": ..., "line": ..., "text": ..., "pattern": ...}]
    """
    try:
        content = filepath.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    violations = []
    lines = content.splitlines()

    for line_num, line in enumerate(lines, 1):
        if is_whitelisted(line):
            continue
        for pattern in FORBIDDEN_PHRASES:
            if re.search(pattern, line, re.IGNORECASE):
                violations.append({
                    "file": str(filepath.relative_to(PROJECT_ROOT)),
                    "line": line_num,
                    "text": line.strip()[:120],
                    "pattern": pattern,
                })

    return violations


# ─────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────

class TestCopyCompliance:

    def test_no_forbidden_phrases_in_backend_copy(self):
        """
        Aucune phrase interdite ne doit apparaître dans les fichiers
        Python du backend (services, routers, schemas).

        GATE PROD BLOQUANT — zéro tolérance (hors whitelist).
        """
        backend_files = [
            f for f in get_files_to_scan()
            if "backend" in str(f) and f.suffix == ".py"
        ]

        if not backend_files:
            pytest.skip("Aucun fichier backend trouvé — vérifie PROJECT_ROOT")

        all_violations = []
        for filepath in backend_files:
            all_violations.extend(scan_file(filepath))

        if all_violations:
            report = "\n".join(
                f"  {v['file']}:{v['line']} — {v['text']}"
                for v in all_violations[:10]  # limiter l'output
            )
            pytest.fail(
                f"{len(all_violations)} phrase(s) interdite(s) détectée(s) :\n{report}"
            )

    def test_no_forbidden_phrases_in_frontend_copy(self):
        """
        Aucune phrase interdite dans les fichiers frontend (.tsx, .ts, .jsx).
        """
        frontend_files = [
            f for f in get_files_to_scan()
            if "frontend" in str(f) and f.suffix in {".tsx", ".ts", ".jsx", ".js"}
        ]

        if not frontend_files:
            pytest.skip("Aucun fichier frontend trouvé (normal si pas encore créé)")

        all_violations = []
        for filepath in frontend_files:
            all_violations.extend(scan_file(filepath))

        if all_violations:
            report = "\n".join(
                f"  {v['file']}:{v['line']} — {v['text']}"
                for v in all_violations[:10]
            )
            pytest.fail(
                f"{len(all_violations)} phrase(s) interdite(s) dans le frontend :\n{report}"
            )

    def test_whitelist_exemptions_allowed(self):
        """
        Les phrases de la whitelist (disclaimers) ne doivent PAS
        être détectées comme violations même si elles contiennent
        des mots-clés interdits.

        Ce test vérifie que la logique de whitelist fonctionne.
        """
        whitelisted_lines = [
            "Cette application n'offre aucune garantie de gain.",
            "EuroMillions est un jeu de hasard indépendant.",
            "Cela n'augmente pas la probabilité de gagner.",
            "À titre informatif et pédagogique.",
            "Score anti-partage : 0.92",
            "Réduire le risque de partager un gain si vous gagnez.",
        ]
        for line in whitelisted_lines:
            assert is_whitelisted(line), (
                f"La ligne suivante devrait être whitelistée mais ne l'est pas :\n  '{line}'"
            )

    def test_forbidden_detection_works(self):
        """
        Vérifie que le scanner détecte bien les vraies violations.
        (Test du test — s'assure que le scanner n'est pas silencieux.)
        """
        # Simuler un fichier avec du contenu interdit
        import tempfile
        test_content = "Maximisez vos chances avec notre stratégie sûre !"

        violations = []
        for pattern in FORBIDDEN_PHRASES:
            if re.search(pattern, test_content, re.IGNORECASE):
                violations.append(pattern)

        assert len(violations) > 0, (
            "Le scanner n'a détecté aucune violation sur un texte manifestement interdit. "
            "Vérifie les patterns FORBIDDEN_PHRASES."
        )

    def test_generation_service_disclaimers_present(self):
        """
        Le GenerationService doit contenir les disclaimers obligatoires.
        Vérifie que la conformité est codée dans la logique métier.
        """
        service_file = PROJECT_ROOT / "backend" / "app" / "services" / "generation_service.py"
        if not service_file.exists():
            pytest.skip("generation_service.py introuvable")

        content = service_file.read_text(encoding="utf-8")

        required_disclaimers = [
            "aucune garantie de gain",
            "jeu de hasard",
            "anti-partage",
        ]
        for disclaimer in required_disclaimers:
            assert disclaimer.lower() in content.lower(), (
                f"Disclaimer obligatoire absent de generation_service.py : '{disclaimer}'"
            )
