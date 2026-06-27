import json
import random
from datetime import datetime
from pathlib import Path

from arclet.alconna import CommandMeta
from arclet.entari import command, metadata
from entari_plugin_user import UserSession
from entari_plugin_database import AsyncSession
from sqlalchemy import select

from tools.rand import random_pick_small

from .model import DrawRecord


metadata(
    name="浅草寺抽签",
    description="每天一次的抽签，包含大凶、凶、末吉、小吉、中吉、吉、大吉七种结果，每种结果对应一首诗",
    author=[{"name": "RF-Tar-Railt", "email": "rf_tar_railt@qq.com"}],
)


root = Path(__file__).parent

with (root / "assets" / "poetries.json").open(encoding="utf-8") as f_obj:
    draw_poetry: list = json.load(f_obj)


def get_draw():
    some_list = [0, 1, 2, 3, 4, 5, 6]  # 大凶，凶，末吉，小吉，中吉，吉，大吉
    probabilities = [0.09, 0.25, 0.06, 0.07, 0.11, 0.25, 0.17]
    draw_num = random_pick_small(some_list, probabilities)
    poetry_data = draw_poetry[draw_num]
    draw_ans = poetry_data["type"]
    text = poetry_data["poetry"][random.randint(1, poetry_data["count"]) - 1]
    return draw_ans, text


# @record("抽签")
# @exclusive
# @accessable


@command.on("抽签", meta=CommandMeta("进行一次抽签, 可以解除", example="$抽签"))
async def draw(sess: UserSession, db_sess: AsyncSession):
    """每日运势抽签"""
    async with db_sess.begin():
        draw_record = await db_sess.get(DrawRecord, sess.user_id)
        if draw_record:
            today = datetime.now()
            if draw_record.date.day == today.day and draw_record.date.month == today.month:
                return f"您今天已经抽过签了哦，运势为{draw_record.answer}"
            answer, poetry = get_draw()
            draw_record.date = today
            draw_record.answer = answer
        else:
            answer, poetry = get_draw()
            draw_record = DrawRecord(id=sess.user_id, answer=answer)
            db_sess.add(draw_record)
    return f"您今日的运势抽签为：{answer}\n{poetry}"


# @record("抽签")
# @exclusive
# @accessable


@command.on("解签", meta=CommandMeta("解除上一次的抽签", example="$解签"))
async def undraw(sess: UserSession, db_sess: AsyncSession):
    """解除上一次的抽签"""
    async with db_sess.begin():
        draw_record = (await db_sess.scalars(select(DrawRecord).where(DrawRecord.id == sess.user_id))).one_or_none()
        if not draw_record:
            return "您今日还未抽签~"
        await db_sess.delete(draw_record)
    return "您已成功解签"
