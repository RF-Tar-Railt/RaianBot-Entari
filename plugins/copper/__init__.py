from io import BytesIO

from arclet.alconna import CommandMeta
from arclet.entari import Image, MessageChain, Session, command, metadata
from arknights_toolkit.copper import draw_copper

metadata(
    name="模拟界园投钱",
    author=[{"name": "RF-Tar-Railt", "email": "rf_tar_railt@qq.com"}],
)
# @alcommand(cmd, send_error=True, post=True)
# @assign("$main")
# @record("投钱")
# @exclusive
# @accessable


@command.on("投钱", meta=CommandMeta("模拟界园投钱", example="$投钱"))
async def draw_cop_(session: Session):
    """模拟界园投钱"""

    img = draw_copper()
    imageio = BytesIO()
    img.save(
        imageio,
        format="JPEG",
        quality=95,
        subsampling=2,
        qtables="web_high",
    )
    return MessageChain(Image.of(raw=imageio, mime="image/jpeg"))
