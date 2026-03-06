"""
test_draw_calendar.py — U4 : Calendrier "Friday Only" (timezone + DST)
=======================================================================

Objectif : garantir que le calcul du prochain vendredi est correct
dans tous les cas, y compris les changements d'heure (DST).

R7 du Risk Register : "Erreur prochain vendredi (timezone/DST)"
Sévérité : 2, Probabilité : 2 → tests obligatoires.

Rappel des règles métier :
  - Vendredi avant 21h00 Paris → tirage CE SOIR (même date)
  - Vendredi après 21h00 Paris → vendredi SUIVANT (+7 jours)
  - N'importe quel autre jour → prochain vendredi
"""

import pytest
from datetime import datetime
from zoneinfo import ZoneInfo

from app.services.draw_calendar import get_next_friday

TZ = ZoneInfo("Europe/Paris")


def friday(year, month, day, hour=10):
    """Crée une datetime un vendredi à l'heure donnée."""
    return datetime(year, month, day, hour, 0, tzinfo=TZ)


# ─────────────────────────────────────────────
# U4-1 : Cas de base
# ─────────────────────────────────────────────

class TestNextFridayBasic:

    def test_next_friday_from_monday(self):
        """Lundi → prochain vendredi (4 jours plus tard)."""
        monday = datetime(2026, 3, 2, 10, 0, tzinfo=TZ)   # lundi 2 mars 2026
        result = get_next_friday(now=monday)
        assert result["date"] == "2026-03-06", f"Attendu 2026-03-06, got {result['date']}"

    def test_next_friday_from_wednesday(self):
        """Mercredi → vendredi de la même semaine (2 jours plus tard)."""
        wednesday = datetime(2026, 3, 4, 10, 0, tzinfo=TZ)
        result = get_next_friday(now=wednesday)
        assert result["date"] == "2026-03-06"

    def test_next_friday_from_thursday(self):
        """Jeudi → vendredi de la même semaine (1 jour plus tard)."""
        thursday = datetime(2026, 3, 5, 10, 0, tzinfo=TZ)
        result = get_next_friday(now=thursday)
        assert result["date"] == "2026-03-06"

    def test_next_friday_from_saturday(self):
        """Samedi → vendredi de la SEMAINE SUIVANTE."""
        saturday = datetime(2026, 3, 7, 10, 0, tzinfo=TZ)
        result = get_next_friday(now=saturday)
        assert result["date"] == "2026-03-13"

    def test_next_friday_from_sunday(self):
        """Dimanche → vendredi de la semaine suivante."""
        sunday = datetime(2026, 3, 8, 10, 0, tzinfo=TZ)
        result = get_next_friday(now=sunday)
        assert result["date"] == "2026-03-13"


# ─────────────────────────────────────────────
# U4-2 : Règle du vendredi (avant/après 21h)
# ─────────────────────────────────────────────

class TestNextFridayCutoff:

    def test_next_friday_when_friday_before_cutoff(self):
        """
        Vendredi 15h00 → le tirage est CE SOIR, même date.
        """
        fri_afternoon = friday(2026, 3, 6, hour=15)
        result = get_next_friday(now=fri_afternoon)
        assert result["date"] == "2026-03-06", (
            f"Vendredi 15h → même vendredi, got {result['date']}"
        )

    def test_next_friday_when_friday_at_cutoff_minus_one(self):
        """Vendredi 20h59 → encore ce soir (juste avant la limite)."""
        fri_before = friday(2026, 3, 6, hour=20)
        result = get_next_friday(now=fri_before)
        assert result["date"] == "2026-03-06"

    def test_next_friday_when_friday_after_cutoff(self):
        """
        Vendredi 22h00 → le tirage est PASSÉ, prochain vendredi = +7 jours.
        """
        fri_evening = friday(2026, 3, 6, hour=22)
        result = get_next_friday(now=fri_evening)
        assert result["date"] == "2026-03-13", (
            f"Vendredi 22h → vendredi suivant, got {result['date']}"
        )

    def test_next_friday_exactly_at_cutoff(self):
        """Vendredi pile à 21h00 → tirage passé → vendredi suivant."""
        fri_cutoff = friday(2026, 3, 6, hour=21)
        result = get_next_friday(now=fri_cutoff)
        assert result["date"] == "2026-03-13"


# ─────────────────────────────────────────────
# U4-3 : Changements d'heure (DST)
# ─────────────────────────────────────────────

class TestNextFridayDST:

    def test_next_friday_around_dst_march(self):
        """
        En France, le passage à l'heure d'été a lieu le dernier dimanche
        de mars (fin mars). On vérifie que le calcul reste correct
        dans cette période.

        2026 : passage à l'heure d'été le 29 mars (dimanche)
        → UTC+1 → UTC+2
        """
        # Lundi 30 mars 2026 (après le passage à l'heure d'été)
        monday_after_dst = datetime(2026, 3, 30, 10, 0, tzinfo=TZ)
        result = get_next_friday(now=monday_after_dst)
        assert result["date"] == "2026-04-03", (
            f"Lundi post-DST mars → vendredi 3 avril, got {result['date']}"
        )

        # Vendredi 27 mars 2026 (avant le passage)
        fri_before_dst = datetime(2026, 3, 27, 10, 0, tzinfo=TZ)
        result2 = get_next_friday(now=fri_before_dst)
        assert result2["date"] == "2026-03-27", (
            f"Vendredi avant DST → même vendredi, got {result2['date']}"
        )

    def test_next_friday_around_dst_october(self):
        """
        En France, le retour à l'heure d'hiver a lieu le dernier dimanche
        d'octobre. On vérifie la stabilité autour de cette date.

        2026 : passage à l'heure d'hiver le 25 octobre (dimanche)
        → UTC+2 → UTC+1
        """
        # Mercredi 21 octobre 2026 (avant le passage)
        wed_before = datetime(2026, 10, 21, 10, 0, tzinfo=TZ)
        result = get_next_friday(now=wed_before)
        assert result["date"] == "2026-10-23", (
            f"Mercredi avant DST oct → vendredi 23 oct, got {result['date']}"
        )

        # Lundi 26 octobre 2026 (après le passage)
        mon_after = datetime(2026, 10, 26, 10, 0, tzinfo=TZ)
        result2 = get_next_friday(now=mon_after)
        assert result2["date"] == "2026-10-30", (
            f"Lundi post-DST oct → vendredi 30 oct, got {result2['date']}"
        )


# ─────────────────────────────────────────────
# U4-4 : Format et structure de la réponse
# ─────────────────────────────────────────────

class TestNextFridayResponseFormat:

    def test_response_has_required_keys(self):
        """La réponse doit contenir les clés 'date', 'mode' et 'label'."""
        result = get_next_friday()
        assert "date" in result
        assert "mode" in result
        assert "label" in result

    def test_date_is_iso_format(self):
        """La date retournée doit être au format ISO YYYY-MM-DD."""
        result = get_next_friday()
        date_str = result["date"]
        parts = date_str.split("-")
        assert len(parts) == 3
        assert len(parts[0]) == 4   # année
        assert len(parts[1]) == 2   # mois
        assert len(parts[2]) == 2   # jour

    def test_mode_is_friday_only(self):
        """Le mode retourné doit toujours être 'friday_only' en MVP."""
        result = get_next_friday()
        assert result["mode"] == "friday_only"

    def test_label_contains_vendredi(self):
        """Le label lisible doit contenir 'Vendredi'."""
        result = get_next_friday()
        assert "Vendredi" in result["label"], (
            f"Le label doit contenir 'Vendredi' : {result['label']}"
        )

    def test_result_is_always_a_friday(self):
        """
        Quelle que soit la date d'entrée, le résultat doit toujours
        tomber un vendredi (weekday == 4).
        """
        from datetime import date
        test_dates = [
            datetime(2026, 3, 2, 10, tzinfo=TZ),   # lundi
            datetime(2026, 3, 3, 10, tzinfo=TZ),   # mardi
            datetime(2026, 3, 4, 10, tzinfo=TZ),   # mercredi
            datetime(2026, 3, 5, 10, tzinfo=TZ),   # jeudi
            datetime(2026, 3, 6, 10, tzinfo=TZ),   # vendredi avant 21h
            datetime(2026, 3, 6, 22, tzinfo=TZ),   # vendredi après 21h
            datetime(2026, 3, 7, 10, tzinfo=TZ),   # samedi
            datetime(2026, 3, 8, 10, tzinfo=TZ),   # dimanche
        ]
        for dt in test_dates:
            result = get_next_friday(now=dt)
            result_date = date.fromisoformat(result["date"])
            assert result_date.weekday() == 4, (
                f"Entrée : {dt.strftime('%A %d/%m %Hh')} → "
                f"résultat {result['date']} n'est pas un vendredi "
                f"(weekday={result_date.weekday()})"
            )
