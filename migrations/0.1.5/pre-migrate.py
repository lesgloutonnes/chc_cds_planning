# -*- coding: utf-8 -*-
"""Remappe le skin retiré 'pikachu' vers son remplaçant 'pokemon'."""


def migrate(cr, version):
    cr.execute(
        """
        UPDATE hr_employee
           SET skin_type = 'pokemon'
         WHERE skin_type = 'pikachu'
        """
    )
