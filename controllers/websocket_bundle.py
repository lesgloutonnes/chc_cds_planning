# -*- coding: utf-8 -*-
import logging

from odoo import http
from odoo.addons.bus.controllers.websocket import WebsocketController
from odoo.http import request

_logger = logging.getLogger(__name__)


class ChcWebsocketController(WebsocketController):
    @http.route("/bus/websocket_worker_bundle", type="http", auth="public", cors="*")
    def get_websocket_worker_bundle(self, v=None):
        """Si le bundle JS n'est plus sur disque, on drop l'attachment et on régénère."""
        try:
            return super().get_websocket_worker_bundle(v=v)
        except FileNotFoundError:
            _logger.warning(
                "Bundle websocket absent du filestore, régénération",
                exc_info=False,
            )
            request.env["ir.attachment"].sudo()._chc_purge_missing_image_attachments()
            return super().get_websocket_worker_bundle(v=v)
