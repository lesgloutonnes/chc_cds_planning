# -*- coding: utf-8 -*-
"""Remappe les skins retirés de la Selection (birthday_party, carni).

Les valeurs supprimées d'un fields.Selection restent en base : sans remap,
le formulaire employé afficherait une valeur invalide. On rebascule sur le
skin par défaut (sakura).
"""


def migrate(cr, version):
    cr.execute(
        """
        UPDATE hr_employee
           SET skin_type = 'sakura'
         WHERE skin_type IN ('birthday_party', 'carni')
        """
    )
