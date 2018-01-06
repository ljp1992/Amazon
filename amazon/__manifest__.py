# -*- coding: utf-8 -*-
{
    'name': "亚马逊接口",
    'summary': """
request_report 参数含义需要确认下。start_time,proxies,region,marketplaceids
        """,
    'description': """
    """,
    'author': "青岛欧度软件技术有限责任公司 刘吉平 15254597975",
    'website': "http://www.qdodoo.com",
    'category': 'Uncategorized',
    'version': 'V10-1.0',
    'depends': ['sale', 'purchase'],
    'data': [
        # 'security/ir.model.access.csv',
        'views/menu.xml',
        'views/views.xml',
        'views/templates.xml',
        'views/amazon_shop.xml',
        'views/product_down_sync.xml',
    ],
    'demo': [
        'demo/demo.xml',
    ],
    'application': True,
}