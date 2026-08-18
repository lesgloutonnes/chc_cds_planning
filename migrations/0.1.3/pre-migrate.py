# -*- coding: utf-8 -*-
"""Empêche la suppression des indisponibilités seed au upgrade.

Même principe que la migration 0.1.2 : le fichier
data/init_employee_unavailability_data.xml est retiré du manifest, on force
donc noupdate=True sur ses XML IDs pour qu'Odoo (_process_end) ne supprime
pas les enregistrements encore présents en base.
"""


def migrate(cr, version):
    cr.execute(
        """
        UPDATE ir_model_data
           SET noupdate = TRUE
         WHERE module = 'chc_cds_planning'
           AND name LIKE 'unavailability_%'
        """
    )
