# -*- coding: utf-8 -*-

from io import StringIO

data =  {'ReportRequestInfo': {'Scheduled': {'value': 'false'}, 'StartDate': {'value': '2018-01-05T23:11:41+00:00'}, 'EndDate': {'value': '2018-01-05T23:11:41+00:00'}, 'GeneratedReportId': {'value': '7822312048017536'}, 'value': '\n      ', 'ReportRequestId': {'value': '50880017536'}, 'ReportType': {'value': '_GET_MERCHANT_LISTINGS_DATA_'}, 'SubmittedDate': {'value': '2018-01-05T23:11:41+00:00'}, 'ReportProcessingStatus': {'value': '_DONE_'}, 'CompletedDate': {'value': '2018-01-05T23:12:07+00:00'}, 'StartedProcessingDate': {'value': '2018-01-05T23:11:46+00:00'}}, 'HasNext': {'value': 'false'}, 'value': '\n    '}

print data.get('ReportRequestInfo', {}).get('GeneratedReportId', {}).get('value', '')

