# -*- encoding: utf-8 -*-

from odoo import api, fields, models, registry, _
from odoo.addons.amazon_ept_v10.amazon_emipro_api.mws import Reports,Products
from odoo.exceptions import UserError
import time, base64, csv, threading, datetime
from StringIO import StringIO

path = '/Users/king/Desktop/asin_info.txt'

class active_product_listing_report_ept(models.Model):
    _inherit = "active.product.listing.report.ept"

    @api.multi
    def request_report(self):
        instance = self.instance_id
        seller = self.instance_id.seller_id
        report_type = self.report_type
        if not seller:
            raise Warning('Please select instance')

        proxy_data = seller.get_proxy_server()
        mws_obj = Reports(access_key=str(seller.access_key), secret_key=str(seller.secret_key),
                          account_id=str(seller.merchant_id),
                          region=seller.country_id.amazon_marketplace_code or seller.country_id.code,
                          proxies=proxy_data)

        marketplace_ids = tuple([instance.market_place_id])
        try:
            print 'report_type,marketplace_ids:', report_type, marketplace_ids
            result = mws_obj.request_report(report_type, start_date=None, end_date=None, marketplaceids=marketplace_ids)
            self.update_report_history(result)
        except Exception, e:
            if hasattr(mws_obj, 'parsed_response_error') and type(mws_obj.parsed_response_error) != type(None):
                error = mws_obj.parsed_response_error.parsed or {}
                error_value = error.get('Message', {}).get('value')
                error_value = error_value if error_value else str(mws_obj.response.content)
            else:
                error_value = str(e)
            raise Warning(error_value)

        return True

    @api.model
    def update_report_history(self, request_result):
        result = request_result.parsed
        report_info = result.get('ReportInfo', {})
        report_request_info = result.get('ReportRequestInfo', {})
        request_id = report_state = report_id = False
        if report_request_info:
            request_id = str(report_request_info.get('ReportRequestId', {}).get('value', ''))
            report_state = report_request_info.get('ReportProcessingStatus', {}).get('value', '_SUBMITTED_')
            report_id = report_request_info.get('GeneratedReportId', {}).get('value', False)
        elif report_info:
            report_id = report_info.get('ReportId', {}).get('value', False)
            request_id = report_info.get('ReportRequestId', {}).get('value', False)

        if report_state == '_DONE_' and not report_id:
            self.get_report_list()
        vals = {}
        if not self.report_request_id and request_id:
            vals.update({'report_request_id': request_id})
        if report_state:
            vals.update({'state': report_state})
        if report_id:
            vals.update({'report_id': report_id})
        self.write(vals)
        return True

    @api.multi
    def get_report(self):
        self.ensure_one()
        seller = self.instance_id.seller_id
        if not seller:
            raise Warning('Please select seller')

        proxy_data = seller.get_proxy_server()
        mws_obj = Reports(access_key=str(seller.access_key), secret_key=str(seller.secret_key),
                          account_id=str(seller.merchant_id),
                          region=seller.country_id.amazon_marketplace_code or seller.country_id.code,
                          proxies=proxy_data)
        if not self.report_id:
            return True
        try:
            result = mws_obj.get_report(report_id=self.report_id)
        except Exception, e:
            if hasattr(mws_obj, 'parsed_response_error') and type(mws_obj.parsed_response_error) != type(None):
                error = mws_obj.parsed_response_error.parsed or {}
                error_value = error.get('Message', {}).get('value')
                error_value = error_value if error_value else str(mws_obj.response.content)
            else:
                error_value = str(e)
            raise Warning(error_value)
        result = base64.b64encode(result.parsed)
        file_name = "Active_Product_List_" + time.strftime("%Y_%m_%d_%H%M%S") + '.csv'

        attachment = self.env['ir.attachment'].create({
            'name': file_name,
            'datas': result,
            'datas_fname': file_name,
            'res_model': 'mail.compose.message',
            'type': 'binary'
        })
        self.message_post(body=_("<b>Active Product Report Downloaded</b>"), attachment_ids=attachment.ids)
        self.write({'attachment_id': attachment.id})

        return True


@api.multi
def get_report_request_list(self):
    self.ensure_one()
    seller = self.instance_id.seller_id
    if not seller:
        raise Warning('Please select Seller')

    proxy_data = seller.get_proxy_server()
    mws_obj = Reports(access_key=str(seller.access_key), secret_key=str(seller.secret_key),
                      account_id=str(seller.merchant_id),
                      region=seller.country_id.amazon_marketplace_code or seller.country_id.code, proxies=proxy_data)
    if not self.report_request_id:
        return True
    try:
        result = mws_obj.get_report_request_list(requestids=(self.report_request_id,))
        self.update_report_history(result)

    except Exception, e:
        if hasattr(mws_obj, 'parsed_response_error') and type(mws_obj.parsed_response_error) != type(None):
            error = mws_obj.parsed_response_error.parsed or {}
            error_value = error.get('Message', {}).get('value')
            error_value = error_value if error_value else str(mws_obj.response.content)
        else:
            error_value = str(e)
        raise Warning(error_value)
    list_of_wrapper = []
    list_of_wrapper.append(result)
    has_next = result.parsed.get('HasNext', {}).get('value', 'false')
    while has_next == 'true':
        next_token = result.parsed.get('NextToken', {}).get('value')
        try:
            result = mws_obj.get_report_request_list_by_next_token(next_token)
            self.update_report_history(result)

        except Exception, e:
            if hasattr(mws_obj, 'parsed_response_error') and type(mws_obj.parsed_response_error) != type(None):
                error = mws_obj.parsed_response_error.parsed or {}
                error_value = error.get('Message', {}).get('value')
                error_value = error_value if error_value else str(mws_obj.response.content)
            else:
                error_value = str(e)
            raise Warning(error_value)

        has_next = result.parsed.get('HasNext', {}).get('value', '')
        list_of_wrapper.append(result)
    return True

    @api.multi
    def popup_get_asin_info_wizard(self):
        '''弹框 获取产品信息'''
        return {
            'type': 'ir.actions.act_window',
            'name': u'获取产品信息',
            'view_mode': 'form',
            'view_type': 'form',
            'views': [(self.env.ref('amazon_api.get_asin_info_wizard').id, 'form')],
            'res_model': 'sync.product.wizard',
            'target': 'new',
        }

    @api.multi
    def check_asin_info(self):
        '''检查获取的结果有没有写入到数据库中'''
        attachment = self.env['ir.attachment'].search([
            ('res_model', '=', 'active.product.listing.report.ept'),
            ('res_id', '=', self.id),
            ('name', '=', 'asin_info'),
        ])
        if attachment and len(attachment) == 1:
            data = base64.decodestring(attachment.datas)
            asin_info = eval(data)
            print 'asin数量：',len(asin_info)
            for (asin, val) in asin_info.items():
                print asin
                status = val.get('status', {}).get('value')
                if status != 'Success':
                    print val

    @api.multi
    def get_asin_info_thread(self):
        '''获取产品信息'''
        with api.Environment.manage():
            new_cr = registry(self._cr.dbname).cursor()
            self = self.with_env(self.env(cr=new_cr))
            log = self.create_log(u'正在获取店铺产品信息...') #创建日志
            all_asin = self.get_all_asin(log) #从报告中读取所有asin
            all_asin = set(list(all_asin)[:10])
            asin_info = self.get_asin_info_from_amazon(all_asin, log) #通过接口获取所有aisn的数据
            self.record_asin_info_to_attachment(asin_info) #将获取的数据写入数据库中
            self._cr.commit()
            self._cr.close()

    @api.multi
    def record_asin_info_to_attachment(self, asin_info):
        '''将结果写入数据库中'''
        data = base64.b64encode(str(asin_info))
        attachment = self.env['ir.attachment'].search([
            ('res_model', '=', 'active.product.listing.report.ept'),
            ('res_id', '=', self.id),
            ('name', '=', 'asin_info'),
        ])
        if attachment:
            attachment.datas = data
        else:
            self.env['ir.attachment'].create({
                'name': 'asin_info',
                'datas': data,
                'datas_fname': 'asin_info.csv',
                'res_model': 'active.product.listing.report.ept',
                'res_id': self.id,
                'type': 'binary'
            })

    @api.multi
    def get_asin_info_from_amazon(self, all_asin, log):
        seller = self.instance_id.seller_id
        proxy_data = seller.get_proxy_server()
        marketplaceid = self.instance_id.market_place_id
        mws_obj = Products(access_key=str(seller.access_key), secret_key=str(seller.secret_key),
                           account_id=str(seller.merchant_id),
                           region=seller.country_id.amazon_marketplace_code or seller.country_id.code,
                           proxies=proxy_data)
        asin_info = {}
        asins = []
        asin_count = len(all_asin)
        i = 1
        for asin in all_asin:
            asins.append(asin)
            if len(asins) == 5:
                self.get_data_from_amazon(mws_obj, marketplaceid, asins, asin_info, log)  # 获取亚马逊数据
                asins = []
                if i % 10 == 0:
                    log.message = u'正在获取店铺产品信息... 一共%d个产品 已获取%d个产品' % (asin_count, i)
                    self._cr.commit()
            if i == asin_count:
                if asins:
                    self.get_data_from_amazon(mws_obj, marketplaceid, asins, asin_info, log)  # 获取亚马逊数据
                log.message = u'获取店铺产品信息完成！一共%d个产品，用时%s' % (asin_count, self.get_del_time(log.create_date))
                self._cr.commit()
            i += 1
        return asin_info

    def get_del_time(self, start_time):
        '''计算所用时间'''
        del_time = datetime.datetime.now() - datetime.datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
        seconds = del_time.seconds
        info = ''
        h = int(seconds / 3600)
        m = int((seconds - (h * 3600)) / 60)
        s = int(seconds - (h * 3600) - (m * 60))
        if h:
            info += '%d小时' % h
        if m:
            info += '%d分' % m
        if s:
            info += '%s秒' % s
        return info

    @api.multi
    def get_data_from_amazon(self, mws_obj, marketplaceid, asins, asin_info, log):
        '''通过亚马逊接口获取数据 每秒可以处理五个asin，若没有获取到，等待1s再获取'''
        data = False
        try:
            data = mws_obj.get_matching_product_for_id(marketplaceid=marketplaceid, type='ASIN', ids=asins)
        except Exception, e:
            time.sleep(1)
            try:
                data = mws_obj.get_matching_product_for_id(marketplaceid=marketplaceid, type='ASIN', ids=asins)
            except Exception, e:
                self.add_log(log, u'%s %s' %  (str(asins), str(e)),)
        finally:
            if data:
                data = data.parsed
                if type(data) is not list:
                    data = [data]
                for item in data:
                    asin = item.get('Id', {}).get('value', '')
                    status = item.get('status', {}).get('value')
                    if status == 'Success':
                        asin_info.update({asin: item})
                    else:
                        self.add_log(log, u'%s %s' % (asins))
            else:
                self.add_log(log, u'%s 没有获取到数据' % str(asins))

    @api.multi
    def get_all_asin(self, log):
        '''获得所有的asin'''
        amazon_encoding = self.instance_id.amazon_encodings
        imp_file = StringIO(base64.decodestring((self.attachment_id.datas).decode(amazon_encoding)))
        reader = csv.DictReader(imp_file, delimiter='\t')
        all_asin = set()
        for row in reader:
            asin = row.get('asin1', '')
            if not asin:
                message = u'asin1为空 %s' % str(row)
                self.add_log(log, message)
            # if asin in all_asin:
            #     self.add_log(log, u'存在重复的asin %s' % asin)
            all_asin.add(asin)
        return all_asin

    @api.multi
    def create_log(self, message):
        '''创建日志'''
        model = self.env['ir.model'].search([('model', '=', 'active.product.listing.report.ept')])
        log = self.env['amazon.process.log.book'].create({
            'res_model': model.id,
            'res_id': self.id,
            'application': 'sync_products',
            'instance_id': self.instance_id.id,
            'operation_type': 'import',
            'message': message,
        })
        self._cr.commit()
        return log

    @api.multi
    def add_log(self, log, message):
        '''添加日志'''
        self.env['amazon.transaction.log'].create({
            'job_id': log.id,
            'log_type': 'error',  # not_found,mismatch,error,warning
            'message': message,
        })
        self._cr.commit()

    @api.multi
    def view_log(self):
        '''查看同步产品日志'''
        model = self.env['ir.model'].search([('model', '=', 'active.product.listing.report.ept')])
        return {
            'type': 'ir.actions.act_window',
            'name': u'日志',
            'view_mode': 'tree,form',
            'view_type': 'form',
            'views': [(self.env.ref('amazon_ept_v10.amazon_process_job_tree_view_ept').id, 'tree'),
                      (self.env.ref('amazon_ept_v10.amazon_process_job_form_view_ept').id, 'form')],
            'res_model': 'amazon.process.log.book',
            'domain': [('res_model', '=', model.id),
                       ('res_id', '=', self.id),
                       ('application', '=', 'sync_products'),
                       ('instance_id', '=', self.instance_id.id),
                       ('operation_type', '=', 'import')],
            'target': 'current',
        }

################################################################################################################

        @api.multi
        def record_asin_info(self):
            with open(path, 'r') as f:
                content = f.read()
                asin_info = eval(content)
                # print 'type(asin_info):',type(asin_info)
                data = base64.b64encode(str(asin_info))
                print 'type(data):', type(data)

                # data = str(asin_info)
                # print 'type(data):', type(data)

                attachment = self.env['ir.attachment'].search([
                    ('res_model', '=', 'active.product.listing.report.ept'),
                    ('res_id', '=', self.id),
                    ('name', '=', 'asin_info'),
                ])
                if attachment:
                    attachment.datas = data
                else:
                    self.env['ir.attachment'].create({
                        'name': 'asin_info',
                        'datas': data,
                        'datas_fname': 'asin_info.csv',
                        'res_model': 'active.product.listing.report.ept',
                        'res_id': self.id,
                        'type': 'binary'
                    })



    # @api.multi
    # def popup_get_asin_info_wizard(self):
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'name': u'获取产品信息',
    #         'view_mode': 'form',
    #         'view_type': 'form',
    #         'views': [(self.env.ref('amazon_api.get_asin_info_wizard').id, 'form')],
    #         'res_model': 'sync.product.wizard',
    #         'target': 'new',
    #     }

    # @api.multi
    # def get_asin_info(self):
    #     '''获取产品信息'''
    #     thread_name = 'get_asin_info'
    #     self.judge_threading_status(thread_name)
    #     log = self.env['amazon.process.log.book'].create_log_qdodoo({
    #         'model_name': 'active.product.listing.report.ept',
    #         'res_id': self.id,
    #         'application': 'sync_products',
    #         'instance_id': self.instance_id.id,
    #         'operation_type': 'import',
    #         'message': u'正在获取店铺产品信息...',
    #     })
    #     self._cr.commit()
    #
    #     t = threading.Thread(target=self.get_ains_info_thread, args=(log,), name=thread_name)
    #     t.start()







    #     return {
    #         'type': 'ir.actions.act_window',
    #         'name': u'日志',
    #         'view_mode': 'form',
    #         'view_type': 'form',
    #         'views': [(self.env.ref('amazon_ept_v10.amazon_process_job_form_view_ept').id, 'form')],
    #         'res_model': 'amazon.process.log.book',
    #         'res_id': log.id,
    #         'target': 'current',
    #     }
    #
    # @api.multi
    # def get_ains_info_thread(self, log):
    #     with api.Environment.manage():
    #         new_cr = registry(self._cr.dbname).cursor()
    #         self = self.with_env(self.env(cr=new_cr))
    #         self.get_info_from_amazon(log)
    #         self._cr.commit()
    #         self._cr.close()
    #
    # @api.multi
    # def get_sorted_asin(self, report_data):
    #     '''根据seller-sku规则，给asin排序。把可能为母asin的排在前面，可以减少亚马逊接口查询操作'''
    #     parent_asin = set()
    #     all_asin = report_data.keys()
    #     for asin in all_asin:
    #         if asin == report_data[asin].get('product-id', ''):
    #             parent_asin.add(asin)
    #     other_asin = set(all_asin) - parent_asin
    #     sorted_asin = list(parent_asin) + list(other_asin)
    #     return sorted_asin
    #
    # @api.multi
    # def get_info_from_amazon(self, log):
    #     report_data = self.get_report_info(log)
    #     sorted_asin = self.get_sorted_asin(report_data)
    #     # self.get_asin_info_cs(log)
    #
    # @api.multi
    # def send_requeset_per_five(self, sorted_asin, report_data, log):
    #     '''每五个asin为一组，发送一次请求'''
    #     seller = self.instance_id.seller_id
    #     proxy_data = seller.get_proxy_server()
    #     marketplaceid = self.instance_id.market_place_id
    #     mws_obj = Products(access_key=str(seller.access_key), secret_key=str(seller.secret_key),
    #                        account_id=str(seller.merchant_id),
    #                        region=seller.country_id.amazon_marketplace_code or seller.country_id.code,
    #                        proxies=proxy_data)
    #     asin_query_status = dict.fromkeys(sorted_asin, False)  # 记录asin是否已获得母子关系
    #     product_info = {}  # 记录asin母子关系
    #     asins = []
    #     asin_count = len(sorted_asin)
    #     for i in range(asin_count):
    #         print i + 1
    #         asin = sorted_asin[i]
    #         if not asin_query_status[asin]:
    #             asins.append(asin)
    #             if len(asins) == 5:
    #                 data = self.get_data_from_amazon(mws_obj, marketplaceid, asins, log)  # 获取亚马逊数据
    #                 self.parsed_and_update_data(data, asin_query_status, product_info, report_data, log)
    #                 asins = []
    #         if i + 1 == asin_count and asins:
    #             data = self.get_data_from_amazon(mws_obj, marketplaceid, asins, log)  # 获取亚马逊数据
    #             self.parsed_and_update_data(data, asin_query_status, product_info, report_data, log)
    #     return product_info
    #
    # @api.multi
    # def parsed_and_update_data(self, data, asin_query_status, product_info, report_data, log):
    #     if not data:
    #         return
    #     # 解析amazon api返回的数据
    #     asins_info = self.parsed_data_from_amazon(data, log_rec)
    #     # print '亚马逊返回的数据（解析后）：',asins_info
    #     # 已经获得了母子关系的asin设为True
    #     for (asin, val) in asins_info.items():
    #         asins = [asin]
    #         if val.get('type') == 'parent':
    #             asins += val.get('child_asin')
    #         for item in asins:
    #             asin_query_status[item] = True
    #     # 更新product_info
    #     for (asin, val) in asins_info.items():
    #         if val.get('status') == 'Success':
    #             if val.get('type') in ['parent', '']:
    #                 val.update(report_data[asin])
    #             if val.get('type') == 'parent':
    #                 child_vals = {}
    #                 for child_ain in val['child_asin']:
    #                     if child_ain == asin:
    #                         continue
    #                     child_vals.update({child_ain: report_data[child_ain]})
    #                     child_vals[child_ain]['type'] = 'child'
    #                 val['child_asin'] = child_vals
    #             product_info.update({asin: val})
    #         elif val.get('status') == 'ClientError':
    #             info = u'亚马逊没有查询到产品 %s\n' % (asin)
    #             self.add_log(info, log_rec)
    #
    # @api.multi
    # def parsed_data_from_amazon(self, data, log):
    #     '''解析amazon api返回的数据'''
    #     asins_info = {}
    #     data = data.parsed
    #     if type(data) is not list:
    #         data = [data]
    #     for item in data:
    #         asin = item.get('Id', {}).get('value', '')
    #         status = item.get('status', {}).get('value', {})
    #         Relationships = item.get('Products', {}).get('Product', {}).get('Relationships', {})
    #         if Relationships == {}:
    #             asins_info.update({asin: {'status': status,
    #                                       'Relationships': '',}})
    #         elif Relationships.has_key('VariationParent'):
    #             parent_asin = Relationships['VariationParent'].get('Identifiers', {}).get('MarketplaceASIN', {}) \
    #                 .get('ASIN', {}).get('value', '')
    #             asins_info.update({asin: {'status': status,
    #                                       'Relationships': 'child',
    #                                       'parent_asin': parent_asin,}})
    #         elif Relationships.has_key('VariationChild'):
    #             child_asin = []
    #             children = Relationships.get('VariationChild')
    #             if type(children) is not list:
    #                 children = [children]
    #             for child in children:
    #                 asin = child.get('Identifiers', {}).get('MarketplaceASIN', {}).get('ASIN', {}).get('value', '')
    #                 child_asin.append(asin)
    #             asins_info.update({asin: {'status': status,
    #                                       'Relationships': 'parent',
    #                                       'child_asin': child_asin}})
    #         else:
    #             info = u'Relationships异常 %s\n' % (str(item))
    #             self.add_log(info, log)
    #     return asins_info
    #
    # @api.multi
    # def get_asin_info_cs(self, log):
    #     seller = self.instance_id.seller_id
    #     proxy_data = seller.get_proxy_server()
    #     marketplaceid = self.instance_id.market_place_id
    #     mws_obj = Products(access_key=str(seller.access_key), secret_key=str(seller.secret_key),
    #                        account_id=str(seller.merchant_id),
    #                        region=seller.country_id.amazon_marketplace_code or seller.country_id.code,
    #                        proxies=proxy_data)
    #     data = self.get_data_from_amazon(mws_obj, marketplaceid, ['B07515DQ46','B077GRYGZQ'], log)  # 获取亚马逊数据
    #     print data.parsed
    #
    # @api.multi
    # def get_data_from_amazon(self, mws_obj, marketplaceid, asins, log):
    #     '''通过亚马逊接口获取数据 每秒可以处理五个asin，若没有获取到，等待1s再获取'''
    #     data = False
    #     try:
    #         data = mws_obj.get_matching_product_for_id(marketplaceid=marketplaceid, type='ASIN', ids=asins)
    #     except Exception, e:
    #         time.sleep(1)
    #         try:
    #             data = mws_obj.get_matching_product_for_id(marketplaceid=marketplaceid, type='ASIN', ids=asins)
    #         except Exception, e:
    #             print 'error...',e
    #             self.env['amazon.transaction.log'].create_log_line_qdodoo({
    #                 'job_id': log.id,
    #                 'message': u'%s %s' %  (str(asins), str(e)),
    #             })
    #     finally:
    #         return data
    #
    # @api.multi
    # def get_report_info(self, log):
    #     amazon_encoding = self.instance_id.amazon_encodings
    #     imp_file = StringIO(base64.decodestring((self.attachment_id.datas).decode(amazon_encoding)))
    #     reader = csv.DictReader(imp_file, delimiter='\t')
    #     report_data = {}
    #     for row in reader:
    #         # print type(row)
    #         # for (key, val) in row.items():
    #         #     print key,': ',val
    #         # break
    #         asin = row.get('asin1', '')
    #         if not asin:
    #             self.env['amazon.transaction.log'].create_log_line_qdodoo({
    #                 'job_id': log.id,
    #                 'message': u'asin1为空 %s' % str(row),
    #             })
    #         report_data.update({asin: row})
    #         # fulfillment_by = self.get_fulfillment_type(row.get('fulfillment-channel', ''))
    #         # if not fulfillment_by:
    #         #     self.env['amazon.transaction.log'].create_log_line_qdodoo({
    #         #         'job_id': log.id,
    #         #         'message': u'fulfillment_by为空 %s' % str(row),
    #         #     })
    #         # print row.get('item-description', ''),type(row.get('item-description', ''))
    #         # break
    #         # report_data.update({asin: {
    #         #     'title': unicode(row.get('item-name', ''), "utf-8", errors='ignore'),
    #         #     'long_description': unicode(row.get('item-description', ''), "utf-8", errors='ignore'),
    #         #     'seller_sku': row.get('seller-sku', ''),
    #         #     'fulfillment_by': fulfillment_by,
    #         #     'product_asin': asin,
    #         # }})
    #     return report_data
    #
    #
    # @api.multi
    # def get_sorted_asin(self, not_exist_asins, report_data):
    #     '''根据seller-sku规则，给asin排序。把可能为母asin的排在前面，可以减少亚马逊接口查询操作'''
    #     parent_asin = set()
    #     for asin in not_exist_asins:
    #         barcode = report_data.get(asin, {}).get('barcode', '')
    #         if asin == barcode:
    #             parent_asin.add(asin)
    #     other_asin = set(not_exist_asins) - parent_asin
    #     sorted_asin = list(parent_asin) + list(other_asin)
    #     return sorted_asin
    #
    #
    # @api.multi
    # def view_log(self):
    #     '''查看日志'''
    #     model = self.env['ir.model'].search([('model', '=', 'active.product.listing.report.ept')])
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'name': u'日志',
    #         'view_mode': 'tree,form',
    #         'view_type': 'form',
    #         'views': [(self.env.ref('amazon_ept_v10.amazon_process_job_tree_view_ept').id, 'tree'),
    #                   (self.env.ref('amazon_ept_v10.amazon_process_job_form_view_ept').id, 'form')],
    #         'res_model': 'amazon.process.log.book',
    #         'domain': [('res_model', '=', model.id),
    #                    ('res_id', '=', self.id),
    #                    ('application', '=', 'sync_products'),
    #                    ('instance_id', '=', self.instance_id.id),
    #                    ('operation_type', '=', 'import')],
    #         'target': 'current',
    #     }










# @api.multi
    # def get_info_from_amazon(self, log):
    #     vals = [
    #         {'name': '1'},
    #         {'type': 'product'},
    #         {'name': '3'}
    #     ]
    #     template_obj = self.env['product.template']
    #     for val in vals:
    #         print 'val:', val
    #         with api.Environment.manage():
    #             new_cr = registry(self._cr.dbname).cursor()
    #             self = self.with_env(self.env(cr=new_cr))
    #             try:
    #                 template = template_obj.with_context(create_product_product=False).create(val)
    #                 print template
    #                 self._cr.commit()
    #                 self._cr.close()
    #             except Exception, e:
    #                 self._cr.close()
    #                 print 'error...........'
    #                 print e
    #                 # with api.Environment.manage():
    #                 #     new_cr = registry(self._cr.dbname).cursor()
    #                 #     self = self.with_env(self.env(cr=new_cr))
    #                 #     self.env['amazon.transaction.log'].create_log_line_qdodoo({
    #                 #         'job_id': log.id,
    #                 #         'message': str(e),
    #                 #     })
    #                 #     self._cr.commit()
    #                 #     self._cr.close()
    #     return

    # def create_cs(self, val, log):
    #     with api.Environment.manage():
    #         new_cr = registry(self._cr.dbname).cursor()
    #         self = self.with_env(self.env(cr=new_cr))
    #         try:
    #             template = template_obj.with_context(create_product_product=False).create(val)
    #             print template
    #             self._cr.commit()
    #             self._cr.close()
    #         except Exception, e:
    #             self._cr.close()
    #             print 'error...........'
    #             print e

    # @api.multi
    # def get_info_from_amazon(self, log):
    #     vals = [
    #         {'name':'1'},
    #         {'type':'product'},
    #         {'name':'3'}
    #     ]
    #     template_obj = self.env['product.template']
    #     for val in vals:
    #         print 'val:',val
    #         try:
    #             template_obj.create(val)
    #             print 0
    #             self._cr.commit()
    #             print 1
    #         except Exception, e:
    #             print 2
    #             self._cr.close()
    #             print 3
    #             with api.Environment.manage():
    #                 print 4
    #                 new_cr = registry(self._cr.dbname).cursor()
    #                 self = self.with_env(self.env(cr=new_cr))
    #                 self.env['amazon.transaction.log'].create_log_line_qdodoo({
    #                     'job_id': log.id,
    #                     'message': str(e),
    #                 })
    #                 print 5
    #                 self._cr.commit()
    #                 # self._cr.close()
    #     return

    # @api.multi
    # def get_asin_info(self):
    #     log = self.env['amazon.process.log.book'].create_log_qdodoo({
    #         'model_name': 'active.product.listing.report.ept',
    #         'res_id': self.id,
    #         'application': 'sync_products',
    #         'instance_id': self.instance_id.id,
    #         'operation_type': 'import',
    #         'message': u'正在获取店铺产品信息...',
    #     })
    #
    #     vals = [
    #         {'name': '1'},
    #         {'type': 'product'},
    #         {'name': '3'}
    #     ]

    # for val in vals:
    #     print 'val:', val
    #     result = self.create_product_cs(val)
    #     print self.env.context,self.instance_id.id
    # if result.get('error'):
    #     with api.Environment.manage():
    #         new_cr = registry(self._cr.dbname).cursor()
    #         self = self.with_env(self.env(cr=new_cr))
    #         self.env['amazon.transaction.log'].create_log_line_qdodoo({
    #             'job_id': log.id,
    #             'message': result.get('error'),
    #         })
    #         self._cr.commit()
    #         self._cr.close()

# def create_product_cs(self, val):
#     with api.Environment.manage():
#         new_cr = registry(self._cr.dbname).cursor()
#         self = self.with_env(self.env(cr=new_cr))
#         template_obj = self.env['product.template']
#         try:
#             template = template_obj.with_context(create_product_product=False).create(val)
#             print template
#             self._cr.commit()
#             self._cr.close()
#         except Exception, e:
#             self._cr.close()
#             print 'error...........', e
#             return {'error': str(e)}

