"""CSV 输入适配、错误报告和原子批量写入。"""

import csv
import io
from dataclasses import dataclass, field
from functools import lru_cache

from django.core.exceptions import ValidationError
from django.db import transaction

from funds.forms import FundRecordForm
from funds.models import FundRecord
from funds.permissions import resolve_record_owner

MAX_FILE_SIZE = 10 * 1024 * 1024
MAX_ROWS = 10000
BATCH_SIZE = 100


@dataclass
class ImportResult:
    success_count: int = 0
    error_count: int = 0
    errors: list = field(default_factory=list)


def import_fund_csv(upload, *, actor):
    if not upload.name.lower().endswith('.csv'):
        raise ValidationError('请上传 CSV 格式的文件')
    if upload.size > MAX_FILE_SIZE:
        raise ValidationError('文件过大，最大支持 10MB')
    try:
        content = upload.read(MAX_FILE_SIZE + 1)
        if len(content) > MAX_FILE_SIZE:
            raise ValidationError('文件过大，最大支持 10MB')
        reader = csv.DictReader(
            io.StringIO(content.decode('utf-8-sig')), strict=True
        )
    except UnicodeDecodeError as exc:
        raise ValidationError(
            '文件编码错误，请使用 UTF-8 编码的 CSV 文件'
        ) from exc
    result = ImportResult()
    records = []
    # 缓存仅限本次导入，重复行不会重复查询同一所有者和权限。
    owner_resolver = lru_cache(maxsize=MAX_ROWS)(resolve_record_owner)
    choices = {
        'bank': FundRecord.BANK_CHOICES,
        'category': FundRecord.CATEGORY_CHOICES,
        'savings_status': FundRecord.SAVINGS_STATUS_CHOICES,
    }
    try:
        missing = {'bank', 'category', 'amount'} - set(reader.fieldnames or [])
        if missing:
            raise ValidationError(
                'CSV 文件缺少必要列：' + '、'.join(sorted(missing))
            )
        for count, row in enumerate(reader, start=1):
            if count > MAX_ROWS:
                raise ValidationError(f'文件行数超过限制，最大 {MAX_ROWS} 行')
            data = {
                key: (value or '').strip() for key, value in row.items() if key
            }
            for name, options in choices.items():
                value = data.get(name, '')
                data[name] = dict(
                    (label, code) for code, label in options
                ).get(
                    value,
                    value.upper(),
                )
            form = FundRecordForm(
                data, actor=actor, owner_resolver=owner_resolver
            )
            if not form.is_valid():
                result.error_count += 1
                if len(result.errors) < 5:
                    errors = '；'.join(
                        f'{name}：{"、".join(messages)}'
                        for name, messages in form.errors.items()
                    )
                    result.errors.append(f'第{reader.line_num}行：{errors}')
                continue
            records.append(form.save(commit=False))
    except csv.Error as exc:
        raise ValidationError('CSV 格式错误，请检查引号与列格式') from exc
    with transaction.atomic():
        for start in range(0, len(records), BATCH_SIZE):
            batch_end = start + BATCH_SIZE
            FundRecord.objects.bulk_create(records[start:batch_end])
    result.success_count = len(records)
    return result
