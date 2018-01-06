# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductDownSyncLine(models.Model):
    _name = 'product.down.sync.line'

    message = fields.Text(string=u'错误信息')

    order_id = fields.Many2one('product.down.sync')

