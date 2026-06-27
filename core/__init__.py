import re
import secrets
from base64 import b64decode

from arclet.alconna import config as alconna_config
from arclet.alconna.tools.formatter import MarkdownTextFormatter
from arclet.entari import At, Author, Image, MessageChain, Message, Text, Plugin, metadata
from arclet.entari.plugin import PluginRole
from satori.element import Custom
from satori.client.account import Account
from satori.adapters.qq.utils import parse_file_uri

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
            new[i] = Image(src=url, title=name)
    if cfg.qq_markdown and account.platform == "qq" and new.has(Text):
        in_mds = new.include(Text, Image)
        new = new.exclude(Text, Image)
        if in_mds:
            children_ = []
            for elem in in_mds:
                if isinstance(elem, Image):
                    children_.append(Text(f"![Image]({elem.src})"))
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
