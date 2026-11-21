"""旧页面书签兼容入口，所有写入已迁至版本化 API。"""

from functools import partial

from money_journey.frontend import retired_page

record_list = partial(retired_page, target="/app/funds")
add_record = partial(retired_page, target="/app/funds")
edit_record = partial(retired_page, target="/app/funds")
upload_csv = partial(retired_page, target="/app/operations")
create_snapshot = partial(retired_page, target="/app/operations")
download_csv_template = partial(
    retired_page, target="/api/v1/funds/import-template/"
)
