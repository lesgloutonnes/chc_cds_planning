from datetime import date

from odoo import api, fields, models

from ..utils.friday_rotation import (
    EXCLUDED_EMPLOYEE_CODES,
    collect_friday_pm_counts,
    get_counter_field,
    get_last_date_field,
    get_planning_week_ids_for_fridays_in_year,
)


class FridayRotationCounter(models.Model):
    """Compteur persistant pour la rotation des vendredis PM MLE (FCT et TCH séparés)."""

    _name = "chc_cds_planning.friday_rotation_counter"
    _description = "Compteur rotation vendredi PM MLE"

    employee_id = fields.Many2one(
        "hr.employee", string="Employé", required=True, ondelete="cascade"
    )
    counter_fct = fields.Integer(
        string="Compteur FCT",
        default=0,
        help="Compteur persistant des vendredis PM FCT MLE (jamais les on site)",
    )
    counter_tch = fields.Integer(
        string="Compteur TCH",
        default=0,
        help="Compteur persistant des vendredis PM TCH MLE (jamais les on site ni on site MLE)",
    )
    counter = fields.Integer(
        string="Total vendredis PM MLE",
        compute="_compute_counter",
        store=True,
    )
    last_fct_date = fields.Date(string="Dernier vendredi PM Fonctionnel")
    last_tch_date = fields.Date(string="Dernier vendredi PM Technique")
    last_assignment_date = fields.Date(
        string="Dernier vendredi PM MLE",
        compute="_compute_last_assignment_date",
        store=True,
    )
    last_reset_year = fields.Integer(
        string="Année du dernier reset", default=lambda self: date.today().year
    )

    _sql_constraints = [
        ("employee_unique", "UNIQUE(employee_id)", "Un seul compteur par employé!")
    ]

    @api.depends("counter_fct", "counter_tch")
    def _compute_counter(self):
        for record in self:
            record.counter = record.counter_fct + record.counter_tch

    @api.depends("last_fct_date", "last_tch_date")
    def _compute_last_assignment_date(self):
        for record in self:
            dates = [d for d in (record.last_fct_date, record.last_tch_date) if d]
            record.last_assignment_date = max(dates) if dates else False

    def get_count(self, perm_type_code):
        self.ensure_one()
        return getattr(self, get_counter_field(perm_type_code), 0)

    @api.model
    def get_or_create_counter(self, employee_id):
        counter = self.search([("employee_id", "=", employee_id)], limit=1)
        if not counter:
            counter = self.create({"employee_id": employee_id})
        return counter

    @api.model
    def increment(self, employee_id, perm_type_code, assignment_date):
        if not employee_id or perm_type_code not in ("FCT", "TCH"):
            return
        counter = self.get_or_create_counter(employee_id)
        counter_field = get_counter_field(perm_type_code)
        date_field = get_last_date_field(perm_type_code)
        counter.write(
            {
                counter_field: getattr(counter, counter_field) + 1,
                date_field: assignment_date,
            }
        )

    @api.model
    def check_and_reset_if_new_year(self):
        """Réinitialise les compteurs si nouvelle année."""
        current_year = date.today().year
        counters = self.search([])

        counters_to_reset = counters.filtered(
            lambda c: c.last_reset_year < current_year
        )

        if counters_to_reset:
            counters_to_reset.write(
                {
                    "counter_fct": 0,
                    "counter_tch": 0,
                    "last_fct_date": False,
                    "last_tch_date": False,
                    "last_reset_year": current_year,
                }
            )
            return len(counters_to_reset)
        return 0

    @api.model
    def reset_all_counters(self):
        current_year = date.today().year
        counters = self.search([])
        counters.write(
            {
                "counter_fct": 0,
                "counter_tch": 0,
                "last_fct_date": False,
                "last_tch_date": False,
                "last_reset_year": current_year,
            }
        )

    @api.model
    def rebuild_from_assignments(self, year=None):
        """Recalcule les compteurs depuis les affectations réelles (source de vérité).

        L'année retenue est celle du vendredi (pas du lundi de la semaine),
        pour ne pas rater un 2 janvier dont le lundi est encore en décembre.
        """
        year = year or date.today().year
        mle_site = self.env["chc_cds_planning.site"].search(
            [("code", "=", "MLE")], limit=1
        )
        if not mle_site:
            return

        week_ids = get_planning_week_ids_for_fridays_in_year(self.env, year)
        assignments = self.env["chc_cds_planning.planning_assignment"].browse()
        if week_ids:
            # Filtre SQL large : le décompte précis (année du vendredi,
            # spéciales, doublons, JUAPE) est fait dans collect_friday_pm_counts.
            assignments = self.env["chc_cds_planning.planning_assignment"].search(
                [
                    ("day", "=", "friday"),
                    ("period", "=", "pm"),
                    ("site_id", "=", mle_site.id),
                    ("permanence_type_id.code", "in", ["FCT", "TCH"]),
                    ("planning_week_id", "in", week_ids),
                ],
                order="id",
            )
            assignments = assignments.sorted(
                key=lambda a: a.planning_week_id.start_date or date.min
            )

        counts = collect_friday_pm_counts(assignments, year)

        existing = {
            c.employee_id.id: c
            for c in self.search([])
        }

        for emp_id, data in counts.items():
            if emp_id in existing:
                existing[emp_id].write(
                    {**data, "last_reset_year": year}
                )
            else:
                self.create({"employee_id": emp_id, **data, "last_reset_year": year})

        for emp_id, counter in existing.items():
            if emp_id not in counts:
                counter.write(
                    {
                        "counter_fct": 0,
                        "counter_tch": 0,
                        "last_fct_date": False,
                        "last_tch_date": False,
                        "last_reset_year": year,
                    }
                )

    @api.model
    def load_rotation_state(self, employees):
        """Charge l'état de rotation depuis les compteurs persistants."""
        employee_friday_pm_fct = {}
        employee_friday_pm_tch = {}
        last_fct_dates = {}
        last_tch_dates = {}

        for emp in employees:
            if emp.employee_code in EXCLUDED_EMPLOYEE_CODES:
                continue
            counter = self.search([("employee_id", "=", emp.id)], limit=1)
            employee_friday_pm_fct[emp.id] = counter.counter_fct if counter else 0
            employee_friday_pm_tch[emp.id] = counter.counter_tch if counter else 0
            last_fct_dates[emp.id] = counter.last_fct_date if counter else None
            last_tch_dates[emp.id] = counter.last_tch_date if counter else None

        return {
            "employee_friday_pm_fct": employee_friday_pm_fct,
            "employee_friday_pm_tch": employee_friday_pm_tch,
            "last_fct_dates": last_fct_dates,
            "last_tch_dates": last_tch_dates,
            "friday_pm_mle_assigned": set(),
        }

    @api.model
    def sync_after_assignment_change(self):
        """Synchronise les compteurs après une modification manuelle."""
        if self.env.context.get("skip_friday_counter_sync"):
            return
        self.rebuild_from_assignments()
