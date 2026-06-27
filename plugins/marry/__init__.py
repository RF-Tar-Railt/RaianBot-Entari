from io import BytesIO
from pathlib import Path

from arclet.entari import Session, Image, MessageChain, command, metadata, keeping
from PIL import Image as Img

metadata(
    name="结婚",
    author=[{"name": "RF-Tar-Railt", "email": "rf_tar_railt@qq.com"}],
)

root = Path(__file__).parent


def load_cover():
    img = Img.open(root / "assets" / "marry.png")
    img.thumbnail(img.size)
    return img


cover = keeping("marry_cover", obj_factory=load_cover)


# @alcommand(cmd, post=True, send_error=True)
# @record("marry")
# @exclusive
# @accessable


@command.on("结婚")
async def marry(session: Session):
    try:
        if not (avatar := session.user.avatar):
            return "该平台不支持获取头像"
    except RuntimeError:
        return "该平台不支持获取头像"
    try:
        data = await session.account.download(avatar)
    except Exception:
        return "下载头像失败"
    base = Img.open(BytesIO(data)).resize(cover.size, Img.Resampling.LANCZOS)
    base.paste(cover, (0, 0), cover)
    result = BytesIO()
    base.save(result, format="PNG", quality=90, qtables="web_high")
    return MessageChain(Image.of(raw=result))
