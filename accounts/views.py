"""旧页面书签兼容入口，所有写入已迁至版本化 API。"""

from functools import partial

from money_journey.frontend import retired_page

login = partial(retired_page, target="/app/login")
logout = partial(retired_page, target="/app/login")
register = partial(retired_page, target="/app/register")
create_member = partial(retired_page, target="/app/members")
user_approval_list = partial(retired_page, target="/app/members")
approve_user = partial(retired_page, target="/app/members")
