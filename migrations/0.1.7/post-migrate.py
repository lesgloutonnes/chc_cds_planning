# -*- coding: utf-8 -*-
"""Régénère les assets filestore manquants et réapplique le remap des skins."""


def migrate(cr, version):
    from odoo import SUPERUSER_ID, api

    env = api.Environment(cr, SUPERUSER_ID, {})
    env["ir.attachment"]._chc_purge_missing_image_attachments()
    env["hr.employee"]._chc_remap_removed_skins()
