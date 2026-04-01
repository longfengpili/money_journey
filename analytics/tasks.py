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
        outdated_records = FundRecord.objects.filter(due_date__lt=time_selected, savings_status='ACTIVE').select_related('user').order_by('due_date')
        
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

def clean_old_records():
    """清理过期记录任务"""
    logger.info(f"开始清理过期记录 - {datetime.now()}")
    
    try:
        # 清理3年前的记录
        cutoff_date = timezone.now() - timedelta(days=365 * 3)
        deleted_count, _ = FundRecord.objects.filter(
            created_at__lt=cutoff_date
        ).delete()
        
        logger.info(f"清理完成，删除 {deleted_count} 条过期记录")
        
    except Exception as e:
        logger.error(f"清理失败: {str(e)}")