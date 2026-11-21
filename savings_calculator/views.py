"""旧页面书签兼容入口，所有写入已迁至版本化 API。"""

from functools import partial

from money_journey.frontend import retired_page

calculator_input = partial(retired_page, target="/app/calculator")
calculate = partial(retired_page, target="/app/calculator")
results = partial(retired_page, target="/app/calculator")
