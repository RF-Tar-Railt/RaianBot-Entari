from arclet.entari import BasicConfModel


class MusicConfig(BasicConfModel):
    api: str
    """网易云API 接口"""
    music_share_sign: str
    """音乐分享签名"""
