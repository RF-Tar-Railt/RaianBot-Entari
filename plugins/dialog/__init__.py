import json
import random
import re
from collections import deque
from pathlib import Path

from arclet.alconna import command_manager
from arclet.entari import (
    Entari,
    MessageChain,
    MessageCreatedEvent,
    SendResponse,
    Session,
    listen,
    metadata,
)
from arclet.letoderea import BLOCK, Contexts
from entari_plugin_llm import register_tool
from entari_plugin_llm.exception import ModelNotFoundError
from entari_plugin_llm.manager import LLMSessionManager
from entari_plugin_user import UserSession

metadata(name="通用模板对话", author=[{"name": "RF-Tar-Railt", "email": "rf_tar_railt@qq.com"}])

root = Path(__file__).parent

with (root / "assets" / "templates.json").open(encoding="utf-8") as f_obj:
    dialog_templates: dict = json.load(f_obj)


RECORD = deque(maxlen=16)
LOCKS = {}


@listen(SendResponse)
async def _record(event: SendResponse):
    if event.result and event.session:
        RECORD.append(event.session.event.sn)


@listen(MessageCreatedEvent, priority=18, label="AI 对话")
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


@listen(MessageCreatedEvent, priority=19, label="AI 对话")
async def llm_dialog(
    sess: UserSession, ctx: Contexts, app: Entari, is_reply_me: bool = False, is_notice_me: bool = False
):
    """利用 LLM 进行对话"""
    if sess.session.event.sn in RECORD:
        return BLOCK
    if sess.user.id in LOCKS:
        return BLOCK
    content = sess.session.elements.extract_plain_text().strip()
    nickname = app.config.basic.nickname or "莱安"
    if is_reply_me:
        content = content
    elif is_notice_me and sess.session.account.adapter != "qqbot":
        content = content
    elif content.startswith(nickname):
        content = content[len(nickname) :].strip()
    else:
        return
    try:
        LOCKS.setdefault(sess.user.id, True)
        answer = await LLMSessionManager.chat(
            MessageChain(content),
            session=sess,
            ctx=ctx,
        )
        if answer != "[END_OF_RESPONSE]":
            await sess.send(answer)
    except ModelNotFoundError as e:
        await sess.send(MessageChain(str(e)))
    except Exception as e:
        await sess.send(MessageChain(str(e)))
    finally:
        LOCKS.pop(sess.user.id, False)
    return BLOCK


@register_tool
async def ask_user_for_argument(session: Session, prompt: str, timeout: int = 120):
    """
    向用户询问参数并等待

    Args:
        session (Session): 当前会话对象
        prompt (str): 询问提示语
        timeout (int): 超时时间，单位秒
    Returns:
        str: 用户输入的参数
        null: 等待超时或用户未输入
    """
    resp = await session.prompt(prompt, timeout=timeout)
    if not resp:
        return "未提供必要的信息，无法继续操作"
    return resp.extract_plain_text()


@register_tool
async def list_command():
    """如果用户输入了是一个看似需要执行的指令，通过该工具列出所有可用的指令，方便模型选择。

    Returns:
        str: 返回一个字符串，列出所有可用的指令。
    """
    return command_manager.all_command_help()


@register_tool
async def get_command_help(command_name: str):
    """获取指定指令的帮助信息, 以便模型了解如何使用该指令。

    Args:
        command_name (str): 指令名称。

    Returns:
        str: 返回该指令的帮助信息。
    """
    return (
        command_manager.get_command(command_name)
        .get_help()
        .replace("&#91;", "[")
        .replace("&#93;", "]")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
    )


@register_tool
async def execute_command(session: Session, command_string: str, send_result: bool = True) -> str:
    """执行指定的指令，可以调用多次。例如某个指令可以返回一个中间结果，模型可以根据中间结果再调用其他指令。

    Args:
        session (Session): 当前会话对象。
        command_string (str): 指令字符串，不需要带命令前缀。
        send_result (bool): 是否将指令执行结果发送给用户，一般在确定指令返回的是最终结果后再设置为 True。
    Returns:
        str: 指令执行结果中的字符串。
    """
    result = await session.execute(command_string)
    if result:
        if send_result:
            await session.send(result)
        return MessageChain(result).display()
    return ""
