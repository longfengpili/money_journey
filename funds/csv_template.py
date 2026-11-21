"""CSV 模板响应，访问权限由 API 层校验。"""

import csv

from django.http import HttpResponse


def download_csv_template():
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        'attachment; filename="fund_record_template.csv"'
    )
    writer = csv.writer(response)
    writer.writerow(
        [
            "owner",
            "bank",
            "category",
            "amount",
            "savings_status",
            "interest_rate",
            "deposit_period",
            "due_date",
        ]
    )
    # 所有者留空时归当前账号，管理员可指定家庭成员。
    writer.writerow(
        ["", "ICBC", "SAVINGS", "10000.00", "ACTIVE", "2.5", "1", "2026-12-31"]
    )
    return response
