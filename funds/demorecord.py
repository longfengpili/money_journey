
from datetime import datetime
from decimal import Decimal

from funds.models import FundRecord



class DemoRecord:
    """游客模式演示记录的模拟对象"""
    def __init__(self, id, owner, bank, category, amount, savings_status='ACTIVE',
                 interest_rate=None, deposit_period=None, due_date=None, user=None):
        self.id = id
        self.owner = owner
        self.bank = bank
        self.category = category
        self.amount = Decimal(str(amount))
        self.savings_status = savings_status
        self.interest_rate = Decimal(str(interest_rate)) if interest_rate else None
        self.deposit_period = deposit_period
        self.due_date = due_date
        self.user = user

    def get_bank_display(self):
        return dict(FundRecord.BANK_CHOICES).get(self.bank, self.bank)

    def get_category_display(self):
        return dict(FundRecord.CATEGORY_CHOICES).get(self.category, self.category)

    def get_savings_status_display(self):
        return dict(FundRecord.SAVINGS_STATUS_CHOICES).get(self.savings_status, self.savings_status)

    @property
    def interest_amount(self):
        if self.interest_rate and self.amount and self.deposit_period:
            return float(self.amount) * float(self.interest_rate) * self.deposit_period / 100
        return None


# 游客模式演示数据
DEMO_CURRENT_RECORDS = [
    DemoRecord(1, '张三', 'ICBC', 'CURRENT', 150000, 'ACTIVE'),
    DemoRecord(3, '王五', 'ABC', 'WEALTH_MANAGEMENT', 120000, 'ACTIVE'),
    DemoRecord(2, '李四', 'CCB', 'CURRENT', 80000, 'ACTIVE'),
    DemoRecord(4, '张三', 'BOC', 'FUND', 60000, 'ACTIVE'),
]

DEMO_OTHER_RECORDS = [
    DemoRecord(5, '张三', 'ICBC', 'SAVINGS', 200000, 'ACTIVE', 2.75, 3, datetime(2027, 6, 15)),
    DemoRecord(6, '李四', 'CCB', 'SAVINGS', 150000, 'ACTIVE', 2.50, 1, datetime(2027, 8, 20)),
    DemoRecord(7, '王五', 'ABC', 'SAVINGS', 100000, 'ACTIVE', 3.00, 5, datetime(2028, 3, 10)),
    DemoRecord(8, '张三', 'BOC', 'SAVINGS', 180000, 'ACTIVE', 2.80, 2, datetime(2029, 1, 5)),
    DemoRecord(9, '李四', 'CMB', 'SAVINGS', 120000, 'ACTIVE', 2.60, 3, datetime(2029, 11, 30)),
    DemoRecord(10, '王五', 'ICBC', 'SAVINGS', 80000, 'ACTIVE', 2.40, 1, datetime(2029, 12, 25)),
]

