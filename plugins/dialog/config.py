from arclet.entari.config import BasicConfModel, model_field


class DialogConfig(BasicConfModel):
    noticeme_filter_qqbot: bool = model_field(default=True, description="是否过滤 QQBot 下 @起始的 ai对话请求")
