"""
draw_calendar.py — Calcul du prochain tirage (vendredi)
=========================================================

Ce service calcule la date du prochain tirage EuroMillions.
En mode "friday_only" (MVP), on cherche le prochain vendredi
en timezone Europe/Paris.

POURQUOI LA TIMEZONE ?
EuroMillions se joue en Europe. Le vendredi commence à minuit
heure de Paris, pas UTC. En hiver UTC+1, en été UTC+2 (DST).
On utilise la lib `zoneinfo` (Python 3.9+) pour gérer ça proprement.

RÈGLE MÉTIER :
- Si aujourd'hui est vendredi et qu'il est avant 21h00 (heure Paris)
  → le prochain tirage est CE soir (même vendredi)
- Sinon → vendredi prochain
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.core.config import TIMEZONE

# Timezone Europe/Paris (gère automatiquement l'heure d'été/hiver)
TZ_PARIS = ZoneInfo(TIMEZONE)

# Heure limite de jeu (21h00 Paris) — après cette heure, le tirage est passé
CUTOFF_HOUR = 21

# Noms des jours en français pour le label lisible
FRENCH_WEEKDAYS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
FRENCH_MONTHS = [
    "", "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre"
]


def get_next_friday(now: datetime | None = None) -> dict:
    """
    Calcule le prochain vendredi EuroMillions.

    Args:
        now : datetime de référence (utile pour les tests).
              Si None, utilise l'heure actuelle Paris.

    Returns:
        dict avec :
            date  : str ISO "YYYY-MM-DD"
            mode  : "friday_only"
            label : str lisible "Vendredi 7 mars 2026"
    """
    if now is None:
        now = datetime.now(tz=TZ_PARIS)
    elif now.tzinfo is None:
        # Si la datetime n'a pas de timezone, on suppose Paris
        now = now.replace(tzinfo=TZ_PARIS)

    # weekday() : lundi=0, ..., vendredi=4, samedi=5, dimanche=6
    current_weekday = now.weekday()
    current_hour = now.hour

    if current_weekday == 4 and current_hour < CUTOFF_HOUR:
        # On est vendredi et avant 21h → tirage ce soir
        days_until_friday = 0
    else:
        # Nombre de jours jusqu'au prochain vendredi
        days_until_friday = (4 - current_weekday) % 7
        if days_until_friday == 0:
            # On est vendredi mais après 21h → vendredi prochain (+7j)
            days_until_friday = 7

    next_friday = now.date() + timedelta(days=days_until_friday)

    # Label lisible en français
    label = (
        f"Vendredi {next_friday.day} "
        f"{FRENCH_MONTHS[next_friday.month]} "
        f"{next_friday.year}"
    )

    return {
        "date": next_friday.isoformat(),
        "mode": "friday_only",
        "label": label,
    }
