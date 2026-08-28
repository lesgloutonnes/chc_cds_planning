"""Logique partagée de rotation équitable des vendredis PM MLE."""

from datetime import date, timedelta

EXCLUDED_EMPLOYEE_CODES = frozenset({"JUAPE"})
FRIDAY_PM_PERM_CODES = frozenset({"FCT", "TCH"})


def is_friday_pm_mle_assignment(assignment):
    """Vérifie si une affectation est un vendredi PM MLE FCT/TCH.

    Les permanences on site (HEU/HRM/WAR) et on site MLE (ATL) sont exclues.
    Les permanences spéciales ne comptent pas non plus.
    """
    if not assignment:
        return False
    exists = getattr(assignment, "exists", None)
    if callable(exists) and not exists():
        return False
    if getattr(assignment, "special_name", None):
        return False
    if assignment.day != "friday":
        return False
    if (assignment.period or "").replace(" ", "").lower() != "pm":
        return False
    if not assignment.site_id or assignment.site_id.code != "MLE":
        return False
    if (
        not assignment.permanence_type_id
        or assignment.permanence_type_id.code not in FRIDAY_PM_PERM_CODES
    ):
        return False
    return True


def get_friday_date(week_start):
    return week_start + timedelta(days=4)


def friday_belongs_to_year(week_start, year):
    """True si le vendredi de la semaine (lundi + 4) tombe dans l'année civile."""
    if not week_start or not year:
        return False
    return get_friday_date(week_start).year == year


def get_week_start_range_for_fridays_in_year(year):
    """Bornes inclusives des lundis dont le vendredi tombe dans `year`.

    Un planning est rattaché à son lundi (`start_date`). Un vendredi peut donc
    appartenir à l'année N alors que son lundi est encore en N-1 (ex. vendredi
    2 janvier 2026 → lundi 29 décembre 2025). Inversement, un lundi en N peut
    avoir son vendredi en N+1.
    """
    year_start = date(year, 1, 1)
    year_end = date(year, 12, 31)
    return (year_start - timedelta(days=4), year_end - timedelta(days=4))


def get_planning_week_ids_for_year(env, year):
    """IDs des plannings dont le lundi (`start_date`) est dans l'année civile.

    Sert aux stats de présence (Perm FCT/TCH/Onsite) qui suivent l'appartenance
    des semaines au mois/année du lundi. Ne pas utiliser pour le compteur
    vendredi PM : voir `get_planning_week_ids_for_fridays_in_year`.
    """
    weeks = env["chc_cds_planning.planning_weekly"].search(
        [
            ("start_date", ">=", f"{year}-01-01"),
            ("start_date", "<=", f"{year}-12-31"),
        ],
        order="start_date asc",
    )
    return weeks.ids


def get_planning_week_ids_for_fridays_in_year(env, year):
    """IDs des plannings dont le vendredi tombe dans l'année civile donnée."""
    start_min, start_max = get_week_start_range_for_fridays_in_year(year)
    weeks = env["chc_cds_planning.planning_weekly"].search(
        [
            ("start_date", ">=", start_min),
            ("start_date", "<=", start_max),
        ],
        order="start_date asc",
    )
    return weeks.ids


def collect_friday_pm_counts(assignments, year):
    """Agrège les vendredis PM MLE FCT/TCH d'une année civile.

    - L'année est celle du **vendredi**, pas du lundi de la semaine.
    - Une seule occurrence par (employé, vendredi, type FCT/TCH).
    - JUAPE, on site, permanences spéciales : exclus via
      `is_friday_pm_mle_assignment`.
    """
    counts = {}
    seen = set()
    for assignment in assignments:
        if not is_friday_pm_mle_assignment(assignment):
            continue
        emp = assignment.employee_id
        if not emp or emp.employee_code in EXCLUDED_EMPLOYEE_CODES:
            continue
        week = assignment.planning_week_id
        week_start = week.start_date if week else None
        if not friday_belongs_to_year(week_start, year):
            continue
        perm_code = assignment.permanence_type_id.code
        friday_date = get_friday_date(week_start)
        key = (emp.id, friday_date, perm_code)
        if key in seen:
            continue
        seen.add(key)

        if emp.id not in counts:
            counts[emp.id] = {
                "counter_fct": 0,
                "counter_tch": 0,
                "last_fct_date": False,
                "last_tch_date": False,
            }
        if perm_code == "FCT":
            counts[emp.id]["counter_fct"] += 1
            counts[emp.id]["last_fct_date"] = friday_date
        elif perm_code == "TCH":
            counts[emp.id]["counter_tch"] += 1
            counts[emp.id]["last_tch_date"] = friday_date
    return counts


def get_counter_field(perm_type_code):
    """Retourne le nom du champ compteur pour un type de permanence."""
    return "counter_fct" if perm_type_code == "FCT" else "counter_tch"


def get_last_date_field(perm_type_code):
    return "last_fct_date" if perm_type_code == "FCT" else "last_tch_date"


def find_best_friday_pm_candidate(
    env,
    perm_type_code,
    friday_date,
    rotation_state,
    exclude_employee_ids=None,
):
    """Sélectionne le candidat le plus équitable pour un vendredi PM MLE.

    Critères (par ordre de priorité) :
    1. Qualifié MLE + type de permanence
    2. Disponible le vendredi
    3. Non exclu (JUAPE, déjà en PM MLE cette semaine, ids exclus)
    4. Compteur le plus bas pour ce type (FCT ou TCH)
    5. En cas d'égalité : date de dernière affectation la plus ancienne
    6. En cas d'égalité : id employé (déterministe)
    """
    exclude_employee_ids = exclude_employee_ids or set()
    employees = rotation_state["employees"]
    counter_key = f"employee_friday_pm_{perm_type_code.lower()}"
    counters = rotation_state.get(counter_key, {})
    last_dates = rotation_state.get(f"last_{perm_type_code.lower()}_dates", {})

    mle_site = env["chc_cds_planning.site"].search([("code", "=", "MLE")], limit=1)
    permanence_type = env["chc_cds_planning.permanence_type"].search(
        [("code", "=", perm_type_code)], limit=1
    )
    if not mle_site or not permanence_type:
        return None

    is_available = rotation_state.get("_is_available_fn")
    candidates = []

    for emp in employees:
        if emp.employee_code in EXCLUDED_EMPLOYEE_CODES:
            continue
        if emp.id in exclude_employee_ids:
            continue
        if emp.id in rotation_state.get("friday_pm_mle_assigned", set()):
            continue
        if is_available and not is_available(emp, friday_date):
            continue

        qualification = emp.qualification_ids.filtered(
            lambda q, pt=permanence_type, site=mle_site: q.permanence_type_id.id
            == pt.id
            and q.site_id.id == site.id
        )
        if not qualification:
            continue

        count = counters.get(emp.id, 0)
        last_date = last_dates.get(emp.id)
        candidates.append((emp, count, last_date or date.min, emp.id))

    if not candidates:
        return None

    candidates.sort(key=lambda x: (x[1], x[2], x[3]))
    return candidates[0][0]
