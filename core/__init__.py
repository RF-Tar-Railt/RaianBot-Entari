import re
import secrets
from io import BytesIO
from base64 import b64decode

from arclet.alconna import config as alconna_config
from arclet.alconna.tools.formatter import MarkdownTextFormatter
from arclet.entari import (
    At,
    Author,
    Image,
    Entari,
    MessageCreatedEvent,
    MessageChain,
    Message,
    Text,
    Plugin,
    metadata,
    filter_,
    command,
    Session,
)
from arclet.entari.plugin import PluginRole
from satori.element import Custom
from satori.client.account import Account
from satori.adapters.qq.utils import parse_file_uri
from PIL import Image as PILImage

from tools.cos import CosConfig, put_object
from .config import CoreConfig, cfg
from . import exception, member, request, debug, channel  # noqa: F401


alconna_config.default_namespace.formatter_type = MarkdownTextFormatter
_IMAGE_BASE64_RE = re.compile(r"^data:image/([\w/.+-]+);base64,")

metadata(
    name="核心功能",
    role=PluginRole.UTILITY,
    author=[{"name": "RF-Tar-Railt", "email": "rf_tar_railt@qq.com"}],
    version="0.1.0",
    description="机器人核心功能, 包括腾讯云API的相关功能",
    config=CoreConfig,
)


async def upload_to_cos(content: bytes | str, name: str, custom_domain: bool = False):
    cos_cfg = CosConfig(
        secret_id=cfg.tencentcloud.secret_id,
        secret_key=cfg.tencentcloud.secret_key,
        region=cfg.tencentcloud.region,
        scheme="https",
    )
    await put_object(cos_cfg, cfg.tencentcloud.bucket, content, name, headers={"StorageClass": "STANDARD"})
    return cos_cfg.uri(
        cfg.tencentcloud.bucket,
        name,
        domain=cfg.tencentcloud.custom_domain if custom_domain else None,
    )


plug = Plugin.current()


@plug.use("::before_send")
async def before_send_hook(message: MessageChain, account: Account):
    new = message.fork()
    if cfg.cos_convert or (cfg.qq_markdown and account.platform == "qq"):
        for i, item in enumerate(message):
            if not isinstance(item, Image):
                continue
            if mat := _IMAGE_BASE64_RE.match(item.src):
                base64 = item.src[len(mat.group(0)) :]
                name = f"{item.title or id(item)}_{secrets.token_hex(8)}.png"
                data = b64decode(base64)
            elif item.src.startswith("file://"):
                path = parse_file_uri(item.src)
                name = item.title or path.name
                data = path.read_bytes()
            else:
                continue
            url = await upload_to_cos(data, name, custom_domain=True)
            new[i] = Image(src=url, title=name, width=item.width, height=item.height)
            if not item.width or not item.height:
                try:
                    with BytesIO(data) as f:
                        img = PILImage.open(f)
                        new[i].width, new[i].height = img.size
                except Exception:
                    pass
    if cfg.qq_markdown and account.platform == "qq" and new.has(Text):
        in_mds = new.include(Text, Image, Custom)
        new = new.exclude(Text, Image, Custom)
        if in_mds:
            children_ = []
            for elem in in_mds:
                if isinstance(elem, Image):
                    alt = elem.title or ""
                    if elem.width and elem.height:
                        alt += f" #{elem.width}px #{elem.height}px"
                    children_.append(Text(f"![{alt}]({elem.src})"))
                else:
                    children_.append(elem)
            md = Custom("markdown", children=children_)
            last_at_index = (len(new) - 1 - new[::-1].index(At)) if new.has(At) else len(new)
            new = new[:last_at_index] + [md] + new[last_at_index:]
    elif cfg.long_message_forward:
        for i, item in enumerate(new):
            if isinstance(item, Text) and len(item.text) > 300 and account.platform != "qq":
                msg = Message(forward=True)
                author = Author(id=account.self_id, name=account.self_info.user.name or "莱安")
                for elem in new[i:]:
                    msg.children.append(Message(content=[author, elem]))
                new[i:] = [msg]
                break
    return new


@command.command("手册", "使用说明")
async def usage(sess: Session[MessageCreatedEvent], app: Entari):
    return f"""\
使用说明：
1. {"所有命令都需要@机器人和指令前缀来触发" if sess.account.platform == "qq" else "所有命令都需要指令前缀来触发"}
2. 发送 `{app.config.basic.prefix[0]}帮助` 可以查看所有可用命令
3. 发送 `{app.config.basic.prefix[0]}帮助 [命令]` 可以查看该命令的详细使用说明
4. 发送 `{app.config.basic.prefix[0]}功能 列出` 可以查看所有可用功能
5. 对于管理员，发送 `{app.config.basic.prefix[0]}功能 [功能名] 启用/禁用` 可以在群聊内开启或关闭该功能

{"发送 <qq:inlinecmd enter>免@使用</qq:inlinecmd> 可以查看免@使用说明" if sess.account.platform == "qq" else ""}"""


@(
    plug.dispatch(MessageCreatedEvent)
    .handle()
    .if_(filter_(lambda sess: sess.account.platform == "qq" and sess.content.strip().startswith("免@使用")))
)
async def send_usage(sess: Session[MessageCreatedEvent]):
    await sess.send(
        "免@使用说明：\n"
        "1. 默认情况下，发送消息时需要@机器人和指令前缀才能触发指令。\n"
        "2. 只有群主才能开启免@使用功能。\n"
        "3. 如何开启：群主点击群设置 -> 群机器人 -> 管理机器人 -> 机器人可获取的群聊消息范围，"
        '勾选 "获取群内全部消息"。\n'
        "4. 开启后，机器人将能接收群内所有消息，无需@即可触发指令或消息处理。\n"
        "5. 注意：开启免@使用功能后，机器人将接收群内所有消息，请谨慎使用，以免造成不必要的骚扰或误触发。\n"
        '6. 更进一步可以勾选 "机器人主动在群聊内发言"',
        at_sender=True,
    )
