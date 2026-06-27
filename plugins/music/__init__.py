import asyncio

from arclet.entari import Session, command, plugin_config, metadata, MessageChain, Entari

from satori.element import Custom
from yarl import URL

from .config import MusicConfig


JUMP_URL = "https://music.163.com/song?id={id}"
MUSIC_URL = "https://music.163.com/song/media/outer/url?id={id}.mp3"
cfg = plugin_config(MusicConfig)
base_api = URL(cfg.api)


metadata(
    name="点歌",
    author=[{"name": "RF-Tar-Railt", "email": "rf_tar_railt@qq.com"}],
)


@(
    command.command("点歌 <...content>", "在网易云点歌")
    .usage("可以指定歌手, 与歌名用空格分开")
    .example("$点歌 Rise")
    .config(compact=True)
)
async def song(content: command.Match[MessageChain], app: Entari, sess: Session):
    song_search_url = base_api / "search"
    try:
        async with app.http.get(
            song_search_url, params={"keywords": content.result.extract_plain_text(), "limit": 10}, timeout=20
        ) as resp:
            data = await resp.json()
    except asyncio.TimeoutError:
        return "服务器繁忙中"
    if data["code"] != 200:
        return f"服务器返回错误：{data['message']}"
    if (count := data["result"]["songCount"]) == 0:
        return "没有搜索到呐~换一首歌试试吧！"
    index = 0
    if count > 1:
        await sess.send("查找到多首歌曲；请选择其中一首，限时 15秒")
        result = await sess.prompt(
            "\n".join(
                f"{str(index).rjust(len(str(count)), '0')}. "
                f"{slot['name']} - {', '.join(artist['name'] for artist in slot['artists'])}"
                for index, slot in enumerate(data["result"]["songs"])
            ),
            timeout=15,
        )
        if not result:
            index = 0
        else:
            try:
                index = int(result.extract_plain_text().strip())
            except ValueError:
                return "别捣乱！"
    if index >= count:
        return "别捣乱！"
    song_ = data["result"]["songs"][index]
    song_id = song_["id"]

    song_detail_url = base_api / "song" / "detail"
    async with app.http.get(song_detail_url, params={"ids": song_id}, timeout=20) as resp:
        picture_url = (await resp.json())["songs"][0]["al"]["picUrl"]
    song_summary = f"{song_['name']}--{', '.join(artist['name'] for artist in song_['artists'])}"
    if sess.account.platform in ("qq", "qqguild"):
        ark = Custom(
            "qq:ark24",
            {
                "desc": song_summary,
                "meta_desc": song_summary,
                "prompt": "[音乐分享]",
                "title": song_["name"],
                "subtitle": "网易云",
                "img": picture_url,
                "link": JUMP_URL.format(id=song_id),
            },
        )
        return MessageChain(ark)
    data = {
        "type": "163",
        "url": JUMP_URL.format(id=song_id),
        "audio": MUSIC_URL.format(id=song_id),
        "title": song_["name"],
        "image": picture_url,
        "singer": song_summary,
    }
    async with app.http.post(str(cfg.music_share_sign), json=data) as resp:
        if resp.status != 200:
            return "分享失败"
        json_payload = await resp.text()
        if sess.account.platform == "milky":
            return MessageChain(Custom("milky:light_app", {"json_payload": json_payload}))
        else:
            return MessageChain(Custom("onebot:json", {"data": json_payload}))
