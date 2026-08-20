# -*- coding: utf-8 -*-
import logging
import os

from odoo import api, models

_logger = logging.getLogger(__name__)

_IMAGE_FIELD_PREFIXES = ("image", "avatar", "web_icon")


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    def _chc_is_image_field_attachment(self):
        self.ensure_one()
        field_name = self.res_field or ""
        return field_name.startswith(_IMAGE_FIELD_PREFIXES)

    def _chc_filestore_file_missing(self):
        """True si l'enregistrement pointe vers un fichier disque absent."""
        self.ensure_one()
        if self.type != "binary" or not self.store_fname:
            return False
        try:
            full_path = self._full_path(self.store_fname)
        except (OSError, ValueError):
            return True
        return not os.path.isfile(full_path)

    @api.model
    def _chc_purge_missing_image_attachments(self):
        """Retire photos, icônes et assets JS/CSS dont le fichier filestore n'existe plus.

        Cas typique : copie de base sans filestore. Ouvrir une fiche employé
        tente de lire ``image_128`` / ``avatar_128``. Le bundle
        ``/bus/websocket_worker_bundle`` fait un ``os.stat`` et répond 500.
        """
        attachments = self.sudo().search(
            [
                ("type", "=", "binary"),
                ("store_fname", "!=", False),
                "|",
                ("res_field", "!=", False),
                ("url", "!=", False),
            ]
        )
        missing = attachments.filtered(
            lambda att: (att._chc_is_image_field_attachment() or bool(att.url))
            and att._chc_filestore_file_missing()
        )
        count = len(missing)
        if missing:
            missing.unlink()
        _logger.info(
            "Filestore: %s pièce(s) jointe(s) image/asset absente(s) du disque supprimée(s)",
            count,
        )
        return count
