#!/usr/bin/env python2
import time
import csv
start = time.time()
headers = [
    'seq', 'emplid', 'emplName', 'department', 'date', 'clockin', 'clockout'
]
clockTable = {
    '0013039': {
        'seq': '1',
        'emplid': '0013039',
        'emplName': 'huangwd',
        'department': 'quality',
        'date': '2018-09-20',
        'clockin': '2018-09-20 07:00:00',
        'clockout': '2018-09-20 17:40:00'
    },
    '0013031': {
        'seq': '2',
        'emplid': '0013031',
        'emplName': 't1',
        'department': 'yyy',
        'date': '2018-09-20',
        'clockin': '2018-09-20 07:00:00',
        'clockout': '2018-09-20 17:40:00'
    },
    '0013033': {
        'seq': '3',
        'emplid': '0013033',
        'emplName': 't2',
        'department': 'xxx',
        'date': '2018-09-20',
        'clockin': '2018-09-20 07:00:00',
        'clockout': '2018-09-20 17:40:00'
    }
}

with open('F:/test20180920.csv', 'w', newline='') as f:
    # header
    writer = csv.DictWriter(f, headers)
    writer.writeheader()
    # data write
    # for key in clockTable.keys():
    #     print(key)
    for key, value in clockTable.items():
        writer.writerow(value)
        # print(value)
