# 剩余资金计算引擎
from decimal import Decimal
from datetime import datetime

import logging
logger = logging.getLogger(__name__)

class SavingsCalculator:
    """剩余资金计算引擎"""

    def __init__(self, basic_params, age_range_params):
        """
        初始化计算引擎

        Args:
            basic_params: 基本参数字典
            age_range_params: 年龄段参数列表，每个元素是包含start_age, end_age, monthly_income, monthly_expense的字典
        """
        self.basic_params = basic_params
        self.age_range_params = age_range_params

        # 计算结果存储
        self.results = []  # 按月计算结果列表
        self.deposit_queue = []  # 定期存款队列，存储(月份索引, 金额)

        # 验证参数
        self._validate_params()

    def _validate_params(self):
        """验证参数有效性"""
        if self.basic_params['parent_birth_year'] >= self.basic_params['child_birth_year']:
            raise ValueError("家长出生年份必须早于孩子出生年份")

        # 验证年龄段参数
        age_ranges = []
        for param in self.age_range_params:
            start = param['start_age']
            end = param['end_age']
            if start > end:
                raise ValueError(f"年龄段起始年龄({start})不能大于结束年龄({end})")
            if start < 0 or end < 0:
                raise ValueError("年龄不能为负数")
            age_ranges.append((start, end))

        # 检查年龄段是否覆盖所有可能年龄（可选）
        # 这里不强制要求，允许用户只设置部分年龄段

    def calculate(self, months=None):
        """
        执行计算

        Args:
            months: 计算月数，如果为None则使用basic_params中的calculation_months

        Returns:
            list: 按月计算结果列表
        """
        if months is None:
            months = self.basic_params['calculation_months']

        # 清空之前的结果
        self.results = []

        # 计算开始日期（假设从当前月份开始）
        # start_date = datetime.now().replace(day=1)  # 月份第一天
        start_date = self.calulate_start_date()

        for month_idx in range(months):
            result = self._calculate_month(month_idx, start_date)
            if result:
                self.results.append(result)

        return self.results
    
    def calulate_start_date(self):
        """计算开始日期（以有收入开始为起点计算）"""
        start_age = min(param['start_age'] for param in self.age_range_params)
        return datetime(self.basic_params['parent_birth_year'] + start_age, 1, 1)  # 从有收入的年份的1月1日开始计算

    def _calculate_month(self, month_idx, start_date):
        """计算单个月份"""
        # 计算当前月份日期（手动计算月份偏移）
        year = start_date.year + (start_date.month - 1 + month_idx) // 12
        month = (start_date.month - 1 + month_idx) % 12 + 1
        day = min(start_date.day, 28)  # 避免2月31日等问题

        try:
            current_date = datetime(year, month, day)
        except ValueError:
            # 如果日期无效（如2月30日），使用28日
            current_date = datetime(year, month, 28)

        # 计算年龄
        age = self._calculate_age(current_date, self.basic_params['parent_birth_year'])
        if age >= 80:
            return None
        
        child_age = self._calculate_age(current_date, self.basic_params['child_birth_year'])

        # 获取当前年龄段的收入和支出
        monthly_income, monthly_expense = self._get_income_expense_by_age(age)

        # 获取上个月数据（如果是第一个月，使用初始值）
        prev_month = self.results[-1] if month_idx > 0 else self._get_initial_values()

        # 应用公式计算
        result = self._apply_formulas(month_idx, monthly_income, monthly_expense, prev_month, current_date)

        # 添加年龄信息
        result['month'] = current_date.strftime('%Y-%m')
        result['month_index'] = month_idx
        result['age'] = age
        result['child_age'] = child_age

        return result

    def _calculate_age(self, current_date, birth_year):
        """计算年龄（周岁）"""
        # 简单计算：当前年份减去出生年份
        age = current_date.year - birth_year
        return max(age, 0)

    def _get_income_expense_by_age(self, age):
        """根据年龄获取月收入和月支出"""
        for param in self.age_range_params:
            if param['start_age'] <= age <= param['end_age']:
                return param['monthly_income'], param['monthly_expense']

        # 如果没有匹配的年龄段，返回0
        return Decimal('0'), self.results[-1]['monthly_expense'] if self.results else Decimal('0')  # 如果没有结果，假设支出为0

    def _get_initial_values(self):
        """获取初始值（第0个月之前）"""
        return {
            'regular_transfer': Decimal('0'),  # 定期到期
            'current_deposit_before_expense': Decimal('0'),  # 活期(支出前)
            'regular_deposit_standard': Decimal('0'),  # 定期前金额
            'regular_deposit': Decimal('0'),  # 当月定期储蓄
            'regular_accumulated': Decimal('0'),  # 定期累计
        }

    def _apply_formulas(self, month_idx, monthly_income, monthly_expense, prev_month, current_date):
        """应用所有计算公式"""
        # 1. 计算总支出
        logger.info(f"Calculating month {month_idx}: prev_month={prev_month}, monthly_income={monthly_income}, monthly_expense={monthly_expense}")
        is_annual_expense_month = current_date.month == self.basic_params['annual_expense_month']
        if is_annual_expense_month:
            total_expense = monthly_expense + self.basic_params['annual_expense']
        else:
            total_expense = monthly_expense 

        # 2. 计算活期(支出前)
        current_deposit_before_expense = prev_month['regular_deposit_standard'] - prev_month['regular_deposit']

        # 3. 定期到期（前第36个月到期的钱）
        regular_transfer = self.results[-35]['regular_deposit'] * (1 + self.basic_params['three_year_rate'] / 100 * 3) \
                           if len(self.results) >= 35 else Decimal('0')  # 注意：这里使用前35个月的数据，因为第36个月才到期

        # 4. 计算定期前金额
        regular_deposit_standard = (
            regular_transfer +
            current_deposit_before_expense +
            monthly_income -
            total_expense
        )

        # 6. 计算当月定期储蓄（整万存入，向下取整）
        available_amount = max(Decimal('0'), regular_deposit_standard - self.basic_params['current_amount'])
        if available_amount >= Decimal('10000'):
            regular_deposit = (available_amount // Decimal('10000')) * Decimal('10000')
        else:
            regular_deposit = Decimal('0')

        # 8. 计算定期累计（前35个月当月定期储蓄总和）
        regular_accumulated = self._calculate_regular_accumulated(month_idx, regular_deposit)

        # 10. 计算总计
        total = (
            regular_accumulated - 
            regular_deposit +
            regular_transfer +
            current_deposit_before_expense +
            monthly_income -
            total_expense
        )

        # 9. 返回所有字段
        return {
            'total': total,
            'regular_accumulated': regular_accumulated,
            'regular_transfer': regular_transfer,
            'current_deposit_before_expense': current_deposit_before_expense,
            'regular_deposit_standard': regular_deposit_standard,
            'regular_deposit': regular_deposit,
            'monthly_income': monthly_income,
            'total_expense': total_expense,
            'monthly_expense': monthly_expense,
            'is_annual_expense_month': is_annual_expense_month,
        }

    def _calculate_regular_accumulated(self, month_idx, new_regular_deposit):
        """计算定期累计（前35个月当月定期储蓄总和）"""
        total = Decimal('0')
        for result in self.results[-35:]:  # 只考虑前35个月的当月定期储蓄
            total += result['regular_deposit']
        return total + new_regular_deposit

    def get_summary(self):
        """获取计算摘要"""
        if not self.results:
            return {}

        last_month = self.results[-1]

        # 转换为float以便JSON序列化
        return {
            'total_months': len(self.results),
            'final_total': float(last_month['total']),
            'final_regular_accumulated': float(last_month['regular_accumulated']),
            'final_current_deposit': float(last_month['current_deposit_before_expense']),
            'total_regular_deposit': float(sum(r['regular_deposit'] for r in self.results[-35:])),  # 只统计前35个月的定期储蓄, 其他的到期了
            'total_income': float(sum(r['monthly_income'] for r in self.results)),
            'total_expense': float(sum(r['total_expense'] for r in self.results)),
            'total_balance': float(sum(r['monthly_income'] - r['total_expense'] for r in self.results)),
            'average_monthly_income': float(sum(r['monthly_income'] for r in self.results) / len(self.results)),
            'average_monthly_expense': float(sum(r['monthly_expense'] for r in self.results) / len(self.results)),
        }