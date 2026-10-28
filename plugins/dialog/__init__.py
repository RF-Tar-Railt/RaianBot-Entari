import json
import random
import re
from collections import deque
from pathlib import Path

from arclet.entari import (
    Entari,
    MessageChain,
    MessageCreatedEvent,
    SendResponse,
    Session,
    Reply,
    listen,
    metadata,
    plugin_config,
    command,
    local_data,
    keeping,
)
from arclet.letoderea import BLOCK, Contexts
from entari_plugin_llm.context import group_context
from entari_plugin_llm.exception import ModelNotFoundError
from entari_plugin_llm.manager import LLMSessionManager
from entari_plugin_llm.config import _conf as llm_conf
from entari_plugin_user import UserSession
from satori import ChannelType

from .config import DialogConfig
from . import tools

metadata(name="通用模板对话", author=[{"name": "RF-Tar-Railt", "email": "rf_tar_railt@qq.com"}], config=DialogConfig)

root = Path(__file__).parent

with (root / "assets" / "templates.json").open(encoding="utf-8") as f_obj:
    dialog_templates: dict = json.load(f_obj)


RECORD = deque(maxlen=16)
_conf = plugin_config(DialogConfig)


channel_full_amount_file = local_data.get_data_file("dialog", "allow_full_amount.json")


def _load_data() -> dict:
    if channel_full_amount_file.exists():
        with channel_full_amount_file.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_data(data: dict):
    with channel_full_amount_file.open("w+", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


full_amount: dict[str, list[str]] = keeping(
    "full_amount", obj_factory=_load_data, dispose=_save_data
)


@command.command("全量对话 <switch:开启|关闭|bool>", "开启/关闭全量对话模式")
async def full_amount_command(sess: Session, switch: str | bool):
    """开启/关闭全量对话模式"""
    if isinstance(switch, str):
        switch = switch == "开启"
    token = f"{sess.account.platform}_{sess.account.self_id}"
    if switch:
        full_amount.setdefault(token, []).append(sess.channel.id)
        await sess.send("已开启全量对话模式")
    else:
        full_amount.setdefault(token, []).remove(sess.channel.id)
        await sess.send("已关闭全量对话模式")


@listen(SendResponse)
async def _record(event: SendResponse):
    if event.result and event.session:
        RECORD.append(event.session.event.sn)


@listen(MessageCreatedEvent, priority=2, label="群聊上下文缓存")
async def buffer_group_message(session: Session, event: MessageCreatedEvent):
    """记录群聊消息，供后续对话作为上下文使用"""
    if llm_conf.group_context_limit <= 0 or session.channel.type != ChannelType.TEXT:
        return

    sender = (event.member.nick if event.member else None) or (event.user.nick or event.user.name or event.user.id)
    sender = sender if sender == event.user.id else f"{sender}({event.user.id})"
    group_context.record(
        f"{session.account.platform}:{session.channel.id}",
        message_id=event.message.id,
        sender=sender,
        text=session.content,
    )


@listen(MessageCreatedEvent, priority=18, label="AI-对话")
async def dialog(sess: Session[MessageCreatedEvent], app: Entari):
    content = sess.elements.extract_plain_text().strip()
    ans: str | None = None
    nickname = app.config.basic.nickname or "莱安"
    if content == nickname:
        ans = random.choice(dialog_templates["default"])
    elif content.startswith(nickname):
        for pattern, answers in dialog_templates["patterns"].items():
            if re.fullmatch(pattern, content[len(nickname) :].strip()):
                ans = random.choice(answers)
                break
    if ans:
        await sess.send(ans)
        return BLOCK


@listen(MessageCreatedEvent, priority=19, label="AI-对话")
async def llm_dialog(
    sess: UserSession, ctx: Contexts, app: Entari, reply: Reply | None = None,
    is_reply_me: bool = False, is_notice_me: bool = False
):
    """利用 LLM 进行对话"""
    if sess.session.event.sn in RECORD:
        return BLOCK
    content = sess.session.content
    nickname = app.config.basic.nickname or "莱安"
    if is_reply_me or is_notice_me:
        content = content
    elif content.startswith(nickname):
        content = content[len(nickname) :].strip()
    elif sess.session.channel.id in full_amount.get(f"{sess.account.platform}_{sess.account.self_id}", []):
        content = content
    elif random.random() < llm_conf.get_chance_of(sess.session):
        content = content
    else:
        return
    if _conf.noticeme_filter_qqbot and is_notice_me and sess.account.adapter == "qqbot":
        return
    if reply and reply.quote.children:
        content = content + " " + "".join(map(str, reply.quote.children))
    try:
        answer = await LLMSessionManager.chat(
            MessageChain.of(content),
            session=sess,
            ctx=ctx,
        )
        await LLMSessionManager.send_answer(sess, answer, ctx)
    except ModelNotFoundError as e:
        await sess.send(MessageChain(str(e)))
    except Exception as e:
        await sess.send(MessageChain(str(e)))
    return BLOCK
