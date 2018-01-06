# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.addons.amazon.amazon_api.mws import Reports,Products
import base64, csv
from StringIO import StringIO


class ProductDownSync(models.Model):
    _name = 'product.down.sync'

    name = fields.Char(string=u'编号', default=u'产品同步')
    report_request_id = fields.Char(string=u'ReportRequestId')
    generated_report_id = fields.Char(string=u'GeneratedReportId')

    message = fields.Text(string=u'进度')

    state = fields.Selection([
        ('getting_shop_products', u'正在获取店铺产品'),
        ('getting_asin_info', u'正在获取产品信息'),
        ('done', u'完成'),
        ('error', u'异常'),], default='getting_shop_products', string=u'状态')

    shop_id = fields.Many2one('amazon.shop', string=u'店铺')

    order_line = fields.One2many('product.down.sync.line', 'order_id')

    @api.multi
    def submit_request(self):
        report_type = '_GET_MERCHANT_LISTINGS_DATA_'
        shop = self.shop_id
        mws_obj = Reports(access_key=shop.access_key, secret_key=shop.secret_key, account_id=shop.merchant_id,
                          region=shop.country_id.code, proxies={})
        result = mws_obj.request_report(report_type, start_date=None, end_date=None,
                                        marketplaceids=(shop.market_place_id,))
        data = result.parsed
        print 'submit_request data:',data
        self.report_request_id = data.get('ReportRequestInfo', {}).get('ReportRequestId', {}).get('value', '')

    @api.multi
    def check_request_status(self):
        if not self.report_request_id:
            raise UserError(u'ReportRequestId为空！')
        shop = self.shop_id
        mws_obj = Reports(access_key=shop.access_key, secret_key=shop.secret_key, account_id=shop.merchant_id,
                          region=shop.country_id.code, proxies={})
        result = mws_obj.get_report_request_list(requestids=(self.report_request_id,))
        data = result.parsed
        print 'check_request_status data:', data
        self.generated_report_id = data.get('ReportRequestInfo', {}).get('GeneratedReportId', {}).get('value', '')

    @api.multi
    def get_shop_products(self):
        if not self.generated_report_id:
            raise UserError(u'generated_report_id为空！')
        shop = self.shop_id
        mws_obj = Reports(access_key=shop.access_key, secret_key=shop.secret_key, account_id=shop.merchant_id,
                          region=shop.country_id.code, proxies={})
        result = mws_obj.get_report(report_id=self.generated_report_id)
        data = result.parsed
        print 'get_all_products data:',type(data)
        #将结果写入数据库中
        record_name = 'shop_products'
        fname = 'shop_products.csv'
        data = base64.b64encode(data)
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'product.down.sync'),
            ('res_id', '=', self.id),
            ('name', '=', record_name),
        ])
        if attachments:
            if len(attachments) == 1:
                attachments.datas = data
            else:
                raise UserError(u'存在多个名称为%s的附件' % record_name)
        else:
            self.env['ir.attachment'].create({
                'name': record_name,
                'datas_fname': fname,
                'datas': data,
                'res_model': 'product.down.sync',
                'res_id': self.id,
                'type': 'binary'
            })

    @api.multi
    def get_product_detail_data(self):
        record_name = 'shop_products'
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'product.down.sync'),
            ('res_id', '=', self.id),
            ('name', '=', record_name),
        ])
        if attachments:
            if len(attachments) > 1:
                raise UserError(u'存在多个名称为%s的附件' % record_name)
        else:
            raise UserError(u'没有找到名称为%s的附件' % record_name)
        data = attachments.datas
        encoding = self.shop_id.encoding
        imp_file = StringIO(base64.decodestring(data.decode(encoding)))
        reader = csv.DictReader(imp_file, delimiter='\t')
        for row in reader:
            print row.get('asin1')
        return