import logging
from datetime import datetime, timedelta
from django.utils import timezone
from funds.models import FundRecord
from money_journey.notification import send_pushplus_notification

logger = logging.getLogger(__name__)

def check_outdated_records():
    """检查过期记录任务"""
    logger.info(f"开始检查过期记录 - {datetime.now()}")
    
    try:
        time_selected = timezone.now() + timedelta(days=7)  # 选择未来7天内到期的记录
        outdated_records = FundRecord.objects.filter(due_date__lt=time_selected.date(), savings_status='ACTIVE').select_related('user').order_by('due_date')
        
        if outdated_records.exists():
            records = [f'<br>{record.user.first_name or record.user.username } : {record.get_bank_display()} : {record.due_date} : {record.amount}' for record in outdated_records]
            content = f"{time_selected} 发现 {outdated_records.count()} 条过期记录: {''.join(records)}"
            
            logger.warning(content)
            send_pushplus_notification(
                title="存款到期记录提醒",
                content=content,
                topic='BYD'
            )
        else:
            logger.info("没有发现过期记录")
        
    except Exception as e:
        logger.error(f"检查失败: {str(e)}")

def clean_old_records(*, now=None):
    """只读报告长期未更新的结束状态记录。"""
    current_time = now if now is not None else timezone.now()
    cutoff_date = current_time - timedelta(days=365 * 3)
    count = FundRecord.objects.filter(
        updated_at__lt=cutoff_date,
        savings_status__in=('WITHDRAWN', 'ROLLED_OVER'),
    ).count()
    logger.info(
        '历史记录检查完成，截止 %s，候选 %s 条，数据保留', cutoff_date, count
    )
    return count
