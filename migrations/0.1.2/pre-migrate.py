# -*- coding: utf-8 -*-
"""Empêche la suppression des seeds métier au upgrade.

Quand un fichier data est retiré du manifest, Odoo (_process_end) tente de
supprimer les enregistrements dont l'XML ID n'est plus chargé, si noupdate=False.
On force noupdate=True sur les seeds employés / qualifications / calendrier L1
pour conserver les données déjà en place sans les recharger.
"""


def migrate(cr, version):
    cr.execute(
        """
        UPDATE ir_model_data
           SET noupdate = TRUE
         WHERE module = 'chc_cds_planning'
           AND (
                name LIKE 'employee_%'
             OR name LIKE 'qualif_%'
             OR name LIKE 'l1_guard_%'
           )
        """
    )
