import json
import random
from pathlib import Path

from arclet.alconna import Alconna, Args, CommandMeta, Field, Option
from arclet.entari import At, User, Member, Session, command, metadata


metadata(
    name="发病语录",
    author=[{"name": "RF-Tar-Railt", "email": "rf_tar_railt@qq.com"}],
    description="根据指定模板生成发病语录",
)


json_filename = Path(__file__).parent / "assets" / "templates.json"

with open(json_filename, encoding="UTF-8") as f_obj:
    ill_templates = json.load(f_obj)["templates"]

ill = Alconna(
    "发病",
    Args["name?#你想对谁发病", [str, At]],
    Option(
        "模板|模版",
        Args["template", list(ill_templates.keys()), Field(completion=lambda: list(ill_templates.keys()))],
        dest="tp",
        help_text="指定发病模板",
    ),
    meta=CommandMeta(
        "生成一段模板文字",
        usage="若不指定模板则会随机挑选一个",
        example="$发病 老公",
        extra={"supports": {"mirai"}},
    ),
)


ill_disp = command.mount(ill, skip_for_unmatch=False).as_execute()


@ill_disp.handle()
async def ill_(
    sess: Session, name: command.Match[At | str], template: command.Match[str], user: User, member: Member | None = None
):
    """依据模板发病"""
    if template.available:
        tp = ill_templates[template.result]
    else:
        tp = random.choice(list(ill_templates.values()))
    if name.available:
        _name = name.result
        if isinstance(_name, str):
            text = tp.format(target=_name[:20])
        else:
            if _name.name:
                text = tp.format(target=_name.name[:20])
            elif sess.event.guild:
                target = await sess.account.guild_member_get(sess.event.guild.id, str(_name.id))
                text = tp.format(target=(target.nick or getattr(target.user, "name", str(_name.id)))[:20])
            else:
                target = await sess.account.user_get(str(_name.id))
                text = tp.format(target=(target.name or str(_name.id))[:20])
    else:
        text = tp.format(target=(getattr(member, "nick", None) or user.name or user.id)[:20])
    return ill_disp.finish(text)
