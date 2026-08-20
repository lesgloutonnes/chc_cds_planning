# -*- coding: utf-8 -*-
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class HrLeaveType(models.Model):
    _inherit = "hr.leave.type"

    @api.model
    def _chc_disable_sick_leave_documents(self):
        """DPO : plus de pièces jointes (certificats) sur les types maladie.

        Désactive le champ standard Odoo « documents justificatifs » pour que
        l'UI Time Off n'offre plus l'upload, et que de nouveaux PDF ne soient
        plus écrits dans le filestore.
        """
        if "support_document" not in self._fields:
            return
        sick_types = self.with_context(active_test=False).search(
            [("name", "ilike", "maladie")]
        )
        to_disable = sick_types.filtered("support_document")
        if to_disable:
            to_disable.write({"support_document": False})
            _logger.info(
                "DPO: support_document désactivé sur %s type(s) de congé maladie",
                len(to_disable),
            )

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
