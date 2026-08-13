# -*- coding: utf-8 -*-
from odoo import api, models
from odoo.osv import expression


# Types visibles par les non-admins à la création d'une demande de congé.
EMPLOYEE_REQUESTABLE_LEAVE_TYPE_NAMES = ("Congés", "Maladie", "Congé parental")


class HrLeaveType(models.Model):
    _inherit = "hr.leave.type"

    @api.model
    def _should_filter_employee_leave_types(self):
        """Filtre visuel actif uniquement si le contexte le demande et hors admin planning."""
        return bool(
            self.env.context.get("chc_filter_employee_leave_types")
            and not self.env.user.has_group(
                "chc_cds_planning.group_planning_admin"
            )
        )

    @api.model
    def _search(
        self, domain, offset=0, limit=None, order=None, access_rights_uid=None
    ):
        if self._should_filter_employee_leave_types():
            domain = expression.AND(
                [
                    domain or [],
                    [("name", "in", list(EMPLOYEE_REQUESTABLE_LEAVE_TYPE_NAMES))],
                ]
            )
        return super()._search(
            domain,
            offset=offset,
            limit=limit,
            order=order,
            access_rights_uid=access_rights_uid,
        )
