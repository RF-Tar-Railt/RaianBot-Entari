import inspect

from arclet.alconna import command_manager
from arclet.entari import MessageChain, Session
from arclet.entari.session import STATIC_METHODS, ITERATOR_METHODS
from satori.client import ApiProtocol

from entari_plugin_llm import register_tool


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


funcs = inspect.getmembers(ApiProtocol, predicate=lambda x: inspect.isfunction(x) or inspect.ismethod(x))
apis = [name for name, func in funcs if name not in STATIC_METHODS]
apis.append("internal")


@register_tool
async def list_session_methods():
    """列出所有可用的会话方法，方便模型调用。

    Returns:
        str: 返回一个字符串，列出所有可用的会话方法。
    """
    return "\n".join(apis)


@register_tool
async def get_session_method_details(session: Session, method_name: str):
    """获取指定会话方法的详细信息，包括参数和返回值类型。

    Args:
        session (Session): 当前会话对象。
        method_name (str): 会话方法名称。
    Returns:
        str: 返回该会话方法的详细信息。
    """
    if method_name not in apis:
        return f"方法 {method_name} 不存在。"
    method = getattr(session, method_name, None)
    if not method:
        return f"方法 {method_name} 不存在。"
    return inspect.getdoc(method) or f"方法 {method_name} 没有文档说明。"


@register_tool
async def call_session_method(session: Session, method_name: str, args: dict):
    """调用指定的会话方法，并传入参数。

    Args:
        session (Session): 当前会话对象。
        method_name (str): 会话方法名称。
        args (dict): 方法参数字典。
    Returns:
        str: 方法调用结果的字符串表示。
    """
    if method_name not in apis:
        return f"方法 {method_name} 不存在。"
    method = getattr(session, method_name, None)
    if not method:
        return f"方法 {method_name} 不存在。"
    try:
        if method in ITERATOR_METHODS:
            result = [i async for i in method(**args)]
        else:
            result = await method(**args)
    except Exception as e:
        return f"调用方法 {method_name} 时发生错误: {e!r}"
    return str(result)
