"""旧页面书签兼容入口，所有写入已迁至版本化 API。"""

from functools import partial

from money_journey.frontend import retired_page

dashboard = partial(retired_page, target="/app/")
charts = partial(retired_page, target="/app/")
