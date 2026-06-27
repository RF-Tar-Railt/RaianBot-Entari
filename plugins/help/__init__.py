import random

from entari_plugin_browser import md2img
from satori.element import Custom, Image

from arclet.alconna import Alconna, Args, CommandMeta, Field, command_manager
from arclet.entari import Entari, MessageChain, command, plugin, Session
from arclet.entari.event.command import CommandOutput

from tarina import lang


cmd_help = Alconna(
    "帮助",
    Args[
        "query#选择某条命令的id或者名称查看具体帮助;/?",
        str,
        Field(
            "",
            completion=lambda: f"试试 {random.randint(0, len(command_manager.get_commands()))}",
            unmatch_tips=lambda x: f"预期输入为某个命令的id或者名称，而不是 {x}\n例如：/帮助 0",
        ),
    ],
    meta=CommandMeta("查看帮助"),
)
cmd_help.shortcut(r"帮助(\d+)", {"prefix": True, "args": ["{0}"]})
cmd_help.shortcut("菜单", {"prefix": True})


help_disp = command.mount(cmd_help, skip_for_unmatch=False).as_execute()


@help_disp.handle(label="帮助菜单")
async def help_send(session: Session, query: str, app: Entari):
    if not query:
        md = f"""\
# {session.account.self_info.user.name or "莱安"} {session.account.self_id} 帮助菜单
#{lang.require("manager", "help_header")}

命令前缀：{app.config.basic.prefix}

| id  | 命令 | 介绍 | 备注 |
| --- | --- | --- | --- |
"""
        cmds = list(filter(lambda x: not x.meta.hide, command_manager.get_commands()))
        command_string = "\n".join(
            (
                f"| {index} | {slot.name.replace('|', '&#124;').replace('[', '&#91;')} | "
                f"{slot.meta.description} | {slot.meta.usage.splitlines()[0] if slot.meta.usage else None} |"
            )
            for index, slot in enumerate(cmds)
        )
        md += command_string
        md += """
---
* 输入'命令名 --help' 查看特定命令的语法

* 部分情况下需要先 @机器人本身 才能使用指令（例如当本 bot携带 机器人 标识时）

* 想给点饭钱的话，这里有赞助链接：https://afdian.net/@rf_tar_railt

* 更多功能待开发，如有特殊需求可以向 3165388245 询问, 或前往 122680593 交流
"""
        if session.account.platform == "qq":
            return MessageChain(Custom("markdown", children=[md]))
        img = await md2img(md)
        return MessageChain(Image.of(raw=img, title="help"))
    if query.isdigit():
        cmds = list(command_manager.all_command_raw_help().keys())
        text = command_manager.get_command(cmds[int(query)]).get_help()
    else:
        cmds = list(
            filter(
                lambda x: query in x,
                command_manager.all_command_raw_help().keys(),
            )
        )
        text = command_manager.get_command(cmds[0]).get_help()
    if session.account.platform == "qq":
        return MessageChain(
            Custom(
                "markdown",
                children=[text.replace("&#91;", "[").replace("&#93;", "]").replace("&lt;", "<").replace("&gt;", ">")],
            )
        )
    img = await md2img(text)
    return MessageChain(Image.of(raw=img, title=f"help_{query}"))


@plugin.listen(CommandOutput)
async def convert_md_to_img(event: CommandOutput):
    if event.type == "help":
        if event.session.account.platform == "qq":
            return MessageChain(
                Custom(
                    "markdown",
                    children=[
                        event.content.replace("&#91;", "[")
                        .replace("&#93;", "]")
                        .replace("&lt;", "<")
                        .replace("&gt;", ">")
                    ],
                )
            )
        img = await md2img(event.content)
        return MessageChain(Image.of(raw=img))
