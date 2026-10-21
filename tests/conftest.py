import nonebot
from nonebot.adapters.onebot.v11 import Adapter

nonebot.init(quota_db_path=".pytest_cache/quota.db", superusers=["999"])
nonebot.get_driver().register_adapter(Adapter)
