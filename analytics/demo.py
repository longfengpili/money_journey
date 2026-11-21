"""游客模式演示数据。"""

from datetime import date
from decimal import Decimal

from django.utils import timezone


def demo_maturity_summary():
    """提供标明为演示的未来六个月到期分布。"""
    today = timezone.localdate()
    values = (40000, 200000, 100000, 150000, 0, 250000)
    counts = (1, 2, 1, 2, 0, 2)
    rows = []
    for index, amount in enumerate(values):
        year, month = divmod(today.year * 12 + today.month - 1 + index, 12)
        rows.append({
            'month': date(year, month + 1, 1).strftime('%Y-%m'),
            'total_amount': Decimal(amount),
            'record_count': counts[index],
        })
    return rows


DEMO_DATA = {
    "owner_summary": [
        {
            "owner": "zhangsan",
            "first_name": "张三",
            "total_amount": 580000,
            "record_count": 6,
        },
        {
            "owner": "lisi",
            "first_name": "李四",
            "total_amount": 450000,
            "record_count": 5,
        },
        {
            "owner": "wangwu",
            "first_name": "王五",
            "total_amount": 250000,
            "record_count": 4,
        },
    ],
    "bank_summary": [
        {
            "bank": "ICBC",
            "bank_display": "工商银行",
            "total_amount": 420000,
            "record_count": 4,
        },
        {
            "bank": "CCB",
            "bank_display": "建设银行",
            "total_amount": 350000,
            "record_count": 3,
        },
        {
            "bank": "ABC",
            "bank_display": "农业银行",
            "total_amount": 280000,
            "record_count": 3,
        },
        {
            "bank": "BOC",
            "bank_display": "中国银行",
            "total_amount": 230000,
            "record_count": 3,
        },
        {
            "bank": "CMB",
            "bank_display": "招商银行",
            "total_amount": 2000,
            "record_count": 2,
        },
    ],
    "category_summary": [
        {
            "category": "SAVINGS",
            "category_display": "储蓄存款",
            "total_amount": 680000,
            "record_count": 5,
        },
        {
            "category": "CURRENT",
            "category_display": "活期存款",
            "total_amount": 320000,
            "record_count": 4,
        },
        {
            "category": "WEALTH_MANAGEMENT",
            "category_display": "理财产品",
            "total_amount": 180000,
            "record_count": 3,
        },
        {
            "category": "FUND",
            "category_display": "基金",
            "total_amount": 100000,
            "record_count": 3,
        },
    ],
    "status_summary": [
        {
            "savings_status": "ACTIVE",
            "savings_status_display": "存续中",
            "total_amount": 1280000,
            "record_count": 15,
        },
    ],
    "total_amount": 1280000,
    "total_records": 15,
    "owner_count": 3,
    "category_labels": ["储蓄存款", "活期存款", "理财产品", "基金"],
    "category_totals": [680000.0, 320000.0, 180000.0, 100000.0],
    "bank_labels": [
        "工商银行",
        "建设银行",
        "农业银行",
        "中国银行",
        "招商银行",
    ],
    "bank_totals": [420000.0, 350000.0, 280000.0, 230000.0, 0.0],
    "snapshot_dates": [],
    "snapshot_totals": [],
    "owner_choices": [],
    "has_snapshots": False,
}

_demo_category_amounts = (
    (300000, 150000, 80000, 50000),
    (250000, 100000, 70000, 30000),
    (130000, 70000, 30000, 20000),
)
_demo_category_counts = ((2, 2, 1, 1), (2, 1, 1, 1), (1, 1, 1, 1))
DEMO_DATA['owner_category_summary'] = [
    {
        'owner': owner['owner'],
        'first_name': owner['first_name'],
        'category': category['category'],
        'category_display': category['category_display'],
        'total_amount': amount,
        'record_count': count,
    }
    for owner, amounts, counts in zip(
        DEMO_DATA['owner_summary'], _demo_category_amounts,
        _demo_category_counts,
    )
    for category, amount, count in zip(
        DEMO_DATA['category_summary'], amounts, counts,
    )
]


def filter_demo_category(data, category):
    """按演示数据的类别交叉汇总，保持各视图金额一致。"""
    selected = next(
        (
            row for row in data['category_summary']
            if row['category'] == category
        ),
        None,
    )
    data['category_summary'] = [selected] if selected else []
    data['owner_category_summary'] = [
        row for row in data['owner_category_summary']
        if row['category'] == category
    ]
    data['owner_summary'] = [
        {
            **owner,
            'total_amount': row['total_amount'],
            'record_count': row['record_count'],
        }
        for owner in data['owner_summary']
        for row in data['owner_category_summary']
        if owner['owner'] == row['owner']
    ]
    bank_amounts = {
        'SAVINGS': (220000, 190000, 160000, 110000, 0),
        'CURRENT': (110000, 110000, 100000, 0, 0),
        'WEALTH_MANAGEMENT': (60000, 50000, 0, 70000, 0),
        'FUND': (30000, 0, 20000, 50000, 0),
    }
    amounts = bank_amounts.get(category, ())
    data['bank_summary'] = [
        {**bank, 'total_amount': Decimal(amount), 'record_count': 1}
        for bank, amount in zip(data['bank_summary'], amounts)
        if amount or (
            bank['bank'] == 'CMB' and category in ('SAVINGS', 'CURRENT')
        )
    ]
    data['total_amount'] = (
        selected['total_amount'] if selected else Decimal('0')
    )
    data['total_records'] = selected['record_count'] if selected else 0
    data['owner_count'] = len(data['owner_summary'])
    data['status_summary'] = [
        {**row, 'total_amount': data['total_amount'],
         'record_count': data['total_records']}
        for row in data['status_summary']
    ] if selected else []
    data['maturity_summary'] = []
