# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.addons.amazon.amazon_api.mws import Reports,Products
import base64, csv, io
from StringIO import StringIO

class AmazonShop(models.Model):
    _name = 'amazon.shop'

    name = fields.Char(string=u'名称')
    merchant_id = fields.Char(string=u'merchant_id')
    access_key = fields.Char(string=u'access_key')
    secret_key = fields.Char(string=u'secret_key')
    market_place_id = fields.Char(string=u'market_palce_id')
    amazon_encodings = fields.Char(string=u'编码', help=u'设置正确的编码，才能解析出亚马逊返回的数据')

    note = fields.Text(string=u'备注')

    country_id = fields.Many2one('res.country', string=u'国家')

    @api.multi
    def get_asin_info_cs(self):
        self.read_attachment()
        # asins = ['B076H4DNFF']
        # marketplaceid = self.market_place_id
        # mws_obj = Products(access_key=self.access_key, secret_key=self.secret_key, account_id=self.merchant_id,
        #                    region=self.country_id.code, proxies={})
        # data = mws_obj.get_matching_product_for_id(marketplaceid=marketplaceid, type='ASIN', ids=asins)
        # print data.parsed

    @api.multi
    def read_attachment(self):
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'amazon.shop'),
            ('res_id', '=', self.id),
            ('name', '=', 'shop_products'),
        ])
        if attachments and len(attachments) == 1:
            data = attachments.datas
            print type(data)
            data = data.decode('iso-8859-1')
            print type(data)
            data = base64.decodestring(data)
            print type(data)
            imp_file = StringIO(data)
            reader = csv.DictReader(imp_file, delimiter='\t')
            i = 1
            for row in reader:
                print type(row),row.get('asin1')
                i += 1
                if i > 10:
                    break


    @api.multi
    def get_all_product(self):
        # self.request_report()
        # self.get_report_request_list()
        data = self.get_report()
        self.record_data_to_attachment(data)

    @api.multi
    def request_report(self):
        report_type = '_GET_MERCHANT_LISTINGS_DATA_'
        mws_obj = Reports(access_key=self.access_key, secret_key=self.secret_key, account_id=self.merchant_id,
                           region=self.country_id.code, proxies={})
        result = mws_obj.request_report(report_type, start_date=None, end_date=None,
                                        marketplaceids=(self.market_place_id, ))
        data = result.parsed
        print data
        report_id = data.get('ReportInfo', {}).get('ReportRequestId', {}).get('value', '')
        print report_id

    @api.multi
    def get_report_request_list(self):
        '''hasNext情况没有做'''
        mws_obj = Reports(access_key=self.access_key, secret_key=self.secret_key, account_id=self.merchant_id,
                          region=self.country_id.code, proxies={})
        result = mws_obj.get_report_request_list(requestids=('50880017536',))
        result = result.parsed
        print 'get_report_request_list result:',result
        report_id = result.get('ReportRequestInfo', {}).get('GeneratedReportId', {}).get('value', '')

    @api.multi
    def get_report(self):
        mws_obj = Reports(access_key=self.access_key, secret_key=self.secret_key, account_id=self.merchant_id,
                          region=self.country_id.code, proxies={})

        result = mws_obj.get_report(report_id='7822312048017536')
        data = result.parsed
        print type(data)
        return data

    @api.multi
    def record_data_to_attachment(self, data):
        '''将结果写入数据库中'''
        # amazon_encoding = self.instance_id.amazon_encodings
        # imp_file = StringIO(base64.decodestring((self.attachment_id.datas).decode(amazon_encoding)))
        # reader = csv.DictReader(imp_file, delimiter='\t')
        data = base64.b64encode(data)
        attachment = self.env['ir.attachment'].search([
            ('res_model', '=', 'amazon.shop'),
            ('res_id', '=', self.id),
            ('name', '=', 'shop_products'),
        ])
        if attachment:
            attachment.datas = data
        else:
            self.env['ir.attachment'].create({
                'name': 'shop_products',
                'datas': data,
                'datas_fname': 'shop_products.csv',
                'res_model': 'amazon.shop',
                'res_id': self.id,
                'type': 'binary'
            })

