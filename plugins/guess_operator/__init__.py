import random
from contextlib import suppress
from pathlib import Path

from arclet.alconna import Alconna, Args, CommandMeta, Kw, Option
from arclet.entari import Image, Button, Session, command, local_data, Entari, MessageCreatedEvent, metadata
from arclet.letoderea import step_out
from arknights_toolkit.wordle import Guess, OperatorWordle

from satori import Text, ChannelType
# from satori.element import Custom

metadata(
    name="明日方舟猜干员",
    author=[{"name": "RF-Tar-Railt", "email": "rf_tar_railt@qq.com"}],
)


alc = Alconna(
    "猜干员",
    Args["max_guess", int, 8],
    Args["simple", Kw @ bool, False],
    Option("更新", help_text="更新干员列表"),
    Option("规则", help_text="获取游戏规则"),
    Option("重置", help_text="重置游戏"),
    meta=CommandMeta("明日方舟猜干员游戏", usage="可以指定最大猜测次数", extra={"supports": {"mirai", "qqapi"}}),
)


wordle_data_dir = local_data.get_cache_dir("guess")
wordle = OperatorWordle(str(wordle_data_dir))
root = Path(__file__).parent
guess_cmd = command.mount(alc, skip_for_unmatch=False)


@guess_cmd.assign("规则")
async def guess_info(session: Session):
    img = (root / "assets" / "help.png").read_bytes()
    await session.send([Image.of(raw=img, mime="image/png")])


@guess_cmd.assign("更新")
async def guess_update(session: Session):
    await wordle.update()
    return await session.send("更新完毕")


@guess_cmd.assign("重置")
async def guess_reset(session: Session):
    token = f"{session.account.platform}_{session.account.self_id}_{session.channel.id}"
    if (file := Path(f"{wordle_data_dir / f'{token}.json'}")).exists():
        file.unlink(missing_ok=True)
    return await session.send("重置完毕")


#
# kb = [[
#     Button(
#         RenderData("取消游戏", "取消游戏", 1),
#         Action(2, data="取消", enter=True),
#     ),
#     Button(
#         RenderData("提示", "提示", 1),
#         Action(2, data="提示", enter=True),
#     )
# ]]

kb = [Button.input("取消")("取消游戏"), Button.input("提示")("提示")]

# kb1 = [[
#     Button(
#         RenderData("再来一局！", "再来一局！", 1),
#         Action(2, data="猜干员", enter=True),
#     )
# ]]
kb1 = [Button.input("猜干员")("再来一局！")]


@guess_cmd.assign("$main")
async def guess(
    app: Entari,
    session: Session,
    max_guess: command.Match[int],
    simple: command.Match[bool],
):
    token = f"{session.account.platform}_{session.account.self_id}_{session.channel.id}"
    if (wordle_data_dir / f"{token}.json").exists():
        if token not in await app.cache.get("$guess", []):
            return await session.send("游戏异常，请重置后再试\n重置方法：猜干员 重置")
        await session.send("游戏继续！")
        return

    selected_name, selected = wordle.select(token)
    if session.account.platform == "qq":
        ...
    #         if is_qqapi_group(ctx):
    #             rule_img = Path("assets/image/guess.png").read_bytes()
    #             url = await bot.upload_to_cos(rule_img, f"guess_rule_{token_hex(16)}.png", custom_domain=True)
    #             init_names = random.sample(list(wordle.tables.keys()), 3)
    #             _kb = kb.copy()
    #             _kb.append(
    #                 [
    #                     Button(
    #                         RenderData(init_names[0], init_names[0], 1),
    #                         Action(2, data=init_names[0], enter=True),
    #                     ),
    #                     Button(
    #                         RenderData(init_names[1], init_names[1], 1),
    #                         Action(2, data=init_names[1], enter=True),
    #                     ),
    #                     Button(
    #                         RenderData(init_names[2], init_names[2], 1),
    #                         Action(2, data=init_names[2], enter=True),
    #                     ),
    #                 ]
    #             )
    #             await ctx.scene.send_message(
    #                 [
    #                     Markdown(
    #                         content=f"""\
    # ## 猜干员游戏开始！
    #
    # 请尽量用回复bot的形式发送干员名字
    #
    # 发送 `提示` 或 `@bot 提示` 可以获取提示
    #
    # 发送 `取消` 或 `@bot 取消` 可以结束当前游戏
    #
    # ![#420px #267px]({url})
    # """
    #                     ),
    #                     Keyboard(content=_kb)
    #                 ]
    #             )
    #         else:
    await session.send(
        "猜干员游戏开始！\n"
        "请尽量用回复bot的形式发送干员名字\n"
        "发送 提示 或 @bot 提示 可以获取提示\n"
        "发送 取消 或 @bot 取消 可以结束当前游戏",
    )

    async def waiter(sess1: Session) -> tuple[bool | Guess, Session] | None:
        name = str(sess1.elements[Text]).strip()
        if sess1.channel.id == session.channel.id:
            if name.startswith("取消"):
                await sess1.send("已取消")
                return False, sess1
            if name.startswith("提示"):
                return True, sess1
            with suppress(ValueError):
                return wordle.guess(name, token, max_guess.result), sess1
            return

    guess_cache = await app.cache.get("$guess", [])
    guess_cache.append(session)
    await app.cache.set("$guess", guess_cache)
    siter = step_out(MessageCreatedEvent, waiter, block=session.channel.type is ChannelType.DIRECT)
    async for resp in siter(timeout=120, default=(False, session)):
        if resp is None:
            continue
        res: bool | Guess = resp[0]
        session = resp[1]
        if not res:
            ans = wordle.restart(token)
            guess_cache = await app.cache.get("$guess", [])
            if token in guess_cache:
                guess_cache.remove(token)
                await app.cache.set("$guess", guess_cache)
            return await session.send("游戏已结束！" + (f"\n答案为{ans.select}" if ans else ""))
        if res is True:
            data = {
                "rarity": f"星数：{'★' * (selected['rarity'] + 1)}",
                "career": f"职业：{selected['career']}",
                "race": f"种族：{selected['race']}",
                "org": f"阵营：{selected['org']}",
                "artist": f"画师：{selected['artist']}\n",
            }
            key = random.choice(list(data.keys()))
            await session.send(data[key])
            continue
        try:
            if simple.result:
                await session.send(wordle.draw(res, simple=True, max_guess=max_guess.result))
            else:
                img = wordle.draw(res, max_guess=max_guess.result)
                await session.send([Image.of(raw=img, mime="image/jpeg")])
                # url = None
                # try:
                #     url = await app.upload_to_cos(img, f"guess_{token_hex(16)}.jpg", custom_domain=True)
                #     await session.send(
                #         [
                #             Text(f"{len(res.lines)}/{max_guess.result}\n"),
                #             Custom(
                #                 type="image",
                #                 data={"file": url},
                #             ),
                #         ] + kb if res.state == "guessing" else kb1
                #     )
                # except Exception:
                #     url = url or await app.upload_to_cos(img, f"guess_{token_hex(16)}.jpg")
                #     try:
                #         await session.send(Image.of(url=url))
                #     except Exception:
                #         await session.send(wordle.draw(res, simple=True, max_guess=max_guess.result))
        except Exception as e:
            await session.send(f"{e}")
            break
        if res.state != "guessing":
            break
    wordle.restart(token)
    guess_cache = await app.cache.get("$guess", [])
    if token in guess_cache:
        guess_cache.remove(token)
        await app.cache.set("$guess", guess_cache)
    answer = (
        f"{selected_name}\n"
        f"星数：{'★' * (selected['rarity'] + 1)}\n"
        f"职业：{selected['career']}\n"
        f"种族：{selected['race']}\n"
        f"阵营：{selected['org']}\n"
        f"画师：{selected['artist']}\n"
    )
    return await session.send(f"游戏已结束！\n答案为{answer}")


#     while True:
#         resp = await FunctionWaiter(
#             waiter,
#             [MessageReceived],
#             block_propagation=ctx.client.follows("::friend") or ctx.client.follows("::guild.user"),
#         ).wait(timeout=120, default=(False, ctx))
#         if resp is None:
#             continue
#         res: Union[bool, Guess] = resp[0]
#         ctx = resp[1]
#         if not res:
#             ans = wordle.restart(session)
#             bot.cache["$guess"].remove(session)
#             return await ctx.scene.send_message("游戏已结束！" + (f"\n答案为{ans.select}" if ans else ""))
#         if res is True:
#             data = {
#                 "rarity": f"星数：{'★' * (selected['rarity'] + 1)}",
#                 "career": f"职业：{selected['career']}",
#                 "race": f"种族：{selected['race']}",
#                 "org": f"阵营：{selected['org']}",
#                 "artist": f"画师：{selected['artist']}\n",
#             }
#             key = random.choice(list(data.keys()))
#             await ctx.scene.send_message(data[key])
#             continue
#         try:
#             if simple.result:
#                 await ctx.scene.send_message(wordle.draw(res, simple=True, max_guess=max_guess.result))
#             else:
#                 img = wordle.draw(res, max_guess=max_guess.result)
#                 url = None
#                 try:
#                     if is_qqapi_group(ctx):
#                         url = await bot.upload_to_cos(img, f"guess_{token_hex(16)}.jpg", custom_domain=True)
#                         await ctx.scene.send_message([
#                             Markdown(
#                                 content=f"""\
# {len(res.lines)}/{max_guess.result}
# ![#600px #{80 * (len(res.lines) + 2)}px]({url})
# """,
#                             ),
#                             Keyboard(content=kb1 if res.state != "guessing" else kb)
#                         ])
#                     else:
#                         await ctx.scene.send_message(Picture(RawResource(img)))
#                 except Exception:
#                     url = url or await bot.upload_to_cos(img, f"guess_{token_hex(16)}.jpg")
#                     try:
#                         await ctx.scene.send_message(picture(url, ctx))
#                     except ActionFailed:
#                         await ctx.scene.send_message(wordle.draw(res, simple=True, max_guess=max_guess.result))
#         except Exception as e:
#             await ctx.scene.send_message(f"{e}")
#             break
#         if res.state != "guessing":
#             break
#     wordle.restart(session)
#     bot.cache["$guess"].remove(session)
#     answer = (
#         f"{selected_name}\n"
#         f"星数：{'★' * (selected['rarity'] + 1 )}\n"
#         f"职业：{selected['career']}\n"
#         f"种族：{selected['race']}\n"
#         f"阵营：{selected['org']}\n"
#         f"画师：{selected['artist']}\n"
#     )
#     return await ctx.scene.send_message(f"游戏已结束！\n答案为{answer}")
