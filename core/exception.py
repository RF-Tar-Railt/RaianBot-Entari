import traceback
from contextlib import suppress
from io import StringIO

from arclet.letoderea import ExceptionEvent
from arclet.entari import Entari, listen
from arclet.entari.config import EntariConfig
from entari_plugin_browser import md2img
from satori import Image

from tools.tencentcloud import TencentCloudApi

from .config import cfg


api = TencentCloudApi(
    cfg.tencentcloud.secret_id,
    cfg.tencentcloud.secret_key,
)


@listen(ExceptionEvent, priority=13)
async def report(event: ExceptionEvent, app: Entari):
    # if isinstance(event.exception, NetworkError):
    #     args = event.exception.args
    #     if args[1]["code"] == 500 and "GROUP_CHAT_LIMITED" in args[1]["msg"]:
    #         return
    with StringIO() as fp:
        traceback.print_tb(event.exception.__traceback__, file=fp)
        tb = fp.getvalue()
    data = {
        "event": str(event.origin.__repr__()),
        "exctype": type(event.exception).__name__,
        "exc": repr(event.exception),
        "traceback": tb,
    }
    superusers = EntariConfig.instance.basic.superusers
    qqs = [int(acc) for plat in superusers for acc in superusers[plat] if plat in ("onebot", "milky")]
    if api and qqs:
        with suppress(Exception):
            print(
                await api.send_email(
                    "notice@dunnoaskrf.top",
                    [f"{master}@qq.com" for master in qqs],
                    f"Exception Occur: {type(event.exception).__name__}",
                    27228,
                    data,
                )
            )
    template = """\
## 异常事件：

`{event}`

## 异常类型：

`{exctype}`

## 异常内容：

{exc}

## 异常追踪：

```py
{traceback}
```
"""
    img = await md2img(template.format_map(data), 1500)
    accounts = [acc for acc in app.accounts.values() if acc.platform in ("onebot", "milky")]
    for account in accounts:
        async for friend in account.friend_list():
            if friend.user and int(friend.user.id) in qqs:
                await account.send_private_message(friend.user, [Image.of(raw=img)])
                break
