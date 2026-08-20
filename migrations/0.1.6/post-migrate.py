# -*- coding: utf-8 -*-
"""DPO : retire les certificats médicaux des congés maladie."""


def migrate(cr, version):
    from odoo import SUPERUSER_ID, api

    env = api.Environment(cr, SUPERUSER_ID, {})
    env["hr.leave.type"]._chc_disable_sick_leave_documents()
    env["hr.leave"]._chc_purge_medical_certificate_attachments()
    env["ir.attachment"]._chc_purge_missing_image_attachments()
    env["hr.employee"]._chc_remap_removed_skins()
