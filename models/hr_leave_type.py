# -*- coding: utf-8 -*-
from odoo import api, models


class HrLeaveType(models.Model):
    _inherit = "hr.leave.type"

    @api.model
    def _chc_push_dpi_leave_types_to_end(self):
        """Place les types « Paramétrage DPI » en fin de liste (champ sequence).

        Appelé à chaque mise à jour du module. Tous les utilisateurs voient
        toujours tous les types ; seuls les 3 DPI passent en bas du dropdown.
        """
        dpi_types = self.with_context(active_test=False).search(
            [("name", "ilike", "Paramétrage DPI")],
            order="sequence, id",
        )
        if not dpi_types:
            return

        other_types = self.with_context(active_test=False).search(
            [("id", "not in", dpi_types.ids)],
            order="sequence desc",
            limit=1,
        )
        base_sequence = (other_types.sequence if other_types else 0) + 10

        for index, leave_type in enumerate(dpi_types):
            desired = base_sequence + index
            if leave_type.sequence != desired:
                leave_type.sequence = desired
