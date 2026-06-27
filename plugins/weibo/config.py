from arclet.entari import BasicConfModel


class Config(BasicConfModel):
    cookie: str = ""
    """微博 Cookie, 用于获取用户信息和动态。可电脑访问微博网页端后获取"""

    user_agent: str = ""
    """用户代理, 用于获取用户信息和动态。可电脑访问微博网页端后获取"""

    forward_post: bool | dict[str, bool] = False
    """动态推送是否使用合并转发, 可为每个平台独立设置"""
