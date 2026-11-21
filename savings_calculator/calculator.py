"""不依赖 Django、数据库和系统时钟的储蓄计算引擎。"""

from copy import deepcopy
from datetime import date, datetime
from decimal import Decimal


class SavingsCalculator:
    """使用明确初始输入计算逐月现金流。"""

    def __init__(
        self,
        basic_params,
        age_range_params,
        *,
        start_date,
        initial_current_amount,
        initial_deposits=(),
    ):
        self.basic_params = deepcopy(basic_params)
        self.age_range_params = deepcopy(age_range_params)
        self.start_date = date(start_date.year, start_date.month, 1)
        self._initial_current_amount = initial_current_amount
        self._initial_deposits = tuple(
            tuple(item) for item in initial_deposits
        )
        self.results = []
        self.deposit_queue = list(self._initial_deposits)
        self._validate_params()

    def _validate_params(self):
        """验证参数有效性"""
        if (
            self.basic_params['parent_birth_year']
            >= self.basic_params['child_birth_year']
        ):
            raise ValueError("家长出生年份必须早于孩子出生年份")

        if not self.age_range_params:
            raise ValueError('至少需要设置一个年龄段')

        # 验证年龄段参数
        for param in self.age_range_params:
            start = param['start_age']
            end = param['end_age']
            if start > end:
                raise ValueError(
                    f"年龄段起始年龄({start})不能大于结束年龄({end})"
                )
            if start < 0 or end < 0:
                raise ValueError("年龄不能为负数")

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
        self.deposit_queue = list(self._initial_deposits)
        start_date = self.start_date

        for month_idx in range(months):
            result = self._calculate_month(month_idx, start_date)
            if result is None:
                break
            self.results.append(result)

        return self.results

    def _calculate_month(self, month_idx, start_date):
        """计算单个月份"""
        # 计算当前月份日期（手动计算月份偏移）
        year = start_date.year + (start_date.month - 1 + month_idx) // 12
        month = (start_date.month - 1 + month_idx) % 12 + 1
        current_date = datetime(year, month, 1)

        # 计算年龄
        age = self._calculate_age(
            current_date, self.basic_params['parent_birth_year']
        )
        if age >= 80:
            return None

        child_age = self._calculate_age(
            current_date, self.basic_params['child_birth_year']
        )

        # 获取当前年龄段的收入和支出
        monthly_income, monthly_expense = self._get_income_expense_by_age(age)

        # 获取上个月数据（如果是第一个月，使用初始值）
        prev_month = (
            self.results[-1]
            if self.results
            else self._get_initial_values(current_date)
        )

        # 应用公式计算
        result = self._apply_formulas(
            month_idx,
            monthly_income,
            monthly_expense,
            prev_month,
            current_date,
        )

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
        """根据年龄获取对应的月收入和月支出，优先精确匹配，如果没有匹配则取最近的数据
        当年龄在多个范围重叠时，按照列表顺序返回第一个匹配的
        """
        # 首先检查是否有精确匹配
        for param in self.age_range_params:
            if param['start_age'] <= age <= param['end_age']:
                return param['monthly_income'], param['monthly_expense']

        # 如果没有精确匹配，找到最近的数据
        closest_item = None
        min_distance = float('inf')

        for param in self.age_range_params:
            # 计算与年龄段的距离
            if age < param['start_age']:
                distance = param['start_age'] - age
            elif age > param['end_age']:
                distance = age - param['end_age']
            else:
                distance = 0

            if distance < min_distance:
                min_distance = distance
                closest_item = param

        return (
            Decimal('0'),
            closest_item['monthly_expense'],
        )  # 如果没有匹配的年龄段，返回0收入和最近的支出金额

    def _get_initial_values(self, current_date):
        """获取初始值（第0个月之前）"""

        current_deposit_before_expense = self._initial_current_amount

        regular_transfer = self._calculate_regular_transfer(current_date)
        # 初始定期计算标准等于初始活期金额。
        regular_deposit_standard = current_deposit_before_expense

        return {
            'regular_transfer': regular_transfer,  # 定期到期
            'current_deposit_before_expense': current_deposit_before_expense,
            'regular_deposit_standard': regular_deposit_standard,  # 定期计算标准
            'regular_deposit': Decimal('0'),  # 当月定期储蓄
            'regular_accumulated': Decimal('0'),  # 定期累计
        }

    def _calculate_regular_transfer(self, current_date):
        regular_transfer_list = [
            maturity_amount
            for _, due_date, _, maturity_amount in self.deposit_queue
            if due_date.month == current_date.month
            and due_date.year == current_date.year
        ]
        regular_transfer = (
            sum(regular_transfer_list)
            if regular_transfer_list
            else Decimal('0')
        )
        return regular_transfer

    def _apply_formulas(
        self,
        month_idx,
        monthly_income,
        monthly_expense,
        prev_month,
        current_date,
    ):
        """应用所有计算公式"""
        # 1. 计算总支出
        is_annual_expense_month = (
            current_date.month == self.basic_params['annual_expense_month']
        )
        if is_annual_expense_month:
            total_expense = (
                monthly_expense + self.basic_params['annual_expense']
            )
        else:
            total_expense = monthly_expense

        # 2. 计算活期(支出前)
        current_deposit_before_expense = (
            prev_month['regular_deposit_standard']
            - prev_month['regular_deposit']
        )

        # 3. 定期到期（前第36个月到期的钱）
        regular_transfer = self._calculate_regular_transfer(current_date)

        # 4. 计算定期计算标准
        regular_deposit_standard = (
            regular_transfer
            + current_deposit_before_expense
            + monthly_income
            - total_expense
        )

        # 6. 计算当月定期储蓄（整万存入，向下取整）
        available_amount = max(
            Decimal('0'),
            regular_deposit_standard - self.basic_params['keep_amount'],
        )  # 可用于定期存款的金额，必须保留keep_amount的活期金额
        if available_amount >= Decimal('10000'):
            regular_deposit = (available_amount // Decimal('10000')) * Decimal(
                '10000'
            )
        else:
            regular_deposit = Decimal('0')

        # 7. 将当月定期储蓄加入队列（假设定期利率和存期不变，简单利息计算）
        due_date = current_date.replace(
            year=current_date.year + 3
        ).date()  # 假设定期存3年
        maturity_amount = regular_deposit * (
            1 + self.basic_params['three_year_rate'] / 100 * 3
        )  # 到期金额（假设定期利率不变，简单利息计算）
        self.deposit_queue.append(
            (current_date.date(), due_date, regular_deposit, maturity_amount)
        )  # 将当月定期储蓄加入队列
        self.deposit_queue = [
            fund
            for fund in self.deposit_queue
            if fund[1] > current_date.date()
        ]  # 移除已经到期的定期存款

        # 8. 计算定期累计（未到期）
        regular_accumulated = self._calculate_regular_accumulated(current_date)

        # 9. 计算总计
        total = (
            regular_accumulated
            - regular_deposit
            + regular_transfer
            + current_deposit_before_expense
            + monthly_income
            - total_expense
        )

        # 10. 返回所有字段
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

    def _calculate_regular_accumulated(self, current_date):
        """计算定期累计，只累计未到期的定期储蓄金额"""
        total = Decimal('0')
        for fund in self.deposit_queue:
            start_date, due_date, amount, maturity_amount = fund
            if start_date is None:
                raise ValueError(
                    '初始存款缺少开始日期，请补全资产记录后重新计算'
                )
            if (start_date.year, start_date.month) <= (
                current_date.year,
                current_date.month,
            ) and (due_date.year, due_date.month) > (
                current_date.year,
                current_date.month,
            ):
                total += amount  # 只累计未到期的定期储蓄金额

        return total

    def get_summary(self):
        """获取计算摘要"""
        if not self.results:
            return {}

        last_month = self.results[-1]

        # 转换为float以便JSON序列化
        return {
            'total_months': len(self.results),
            'final_total': float(last_month['total']),
            'final_regular_accumulated': float(
                last_month['regular_accumulated']
            ),
            'final_current_deposit': float(
                last_month['current_deposit_before_expense']
            ),
            'total_regular_deposit': float(
                sum(r['regular_deposit'] for r in self.results[-35:])
            ),  # 只统计前35个月的定期储蓄, 其他的到期了
            'total_income': float(
                sum(r['monthly_income'] for r in self.results)
            ),
            'total_expense': float(
                sum(r['total_expense'] for r in self.results)
            ),
            'total_balance': float(
                sum(
                    r['monthly_income'] - r['total_expense']
                    for r in self.results
                )
            ),
            'average_monthly_income': float(
                sum(r['monthly_income'] for r in self.results)
                / len(self.results)
            ),
            'average_monthly_expense': float(
                sum(r['monthly_expense'] for r in self.results)
                / len(self.results)
            ),
        }
