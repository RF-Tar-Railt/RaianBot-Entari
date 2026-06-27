from arclet.entari import plugin_config
from arclet.entari.config import BasicConfModel


class TencentCloudConfig(BasicConfModel):
    region: str
    """腾讯云API 的 region"""

    secret_id: str
    """腾讯云API 的 secret-id"""

    secret_key: str
    """腾讯云API 的 secret-key"""

    bucket: str
    """腾讯云API 下 COS 的 bucket"""

    custom_domain: str | None = None
    """腾讯云API 下 COS 的自定义域名"""


class CoreConfig(BasicConfModel):
    tencentcloud: TencentCloudConfig
    """腾讯云API 配置"""

    cos_convert: bool = True
    """是否启用COS转换功能, 开启后会将发送的 bytes 图片上传到COS并转换为URL发送,
    以解决部分平台不支持直接发送bytes图片的问题"""

    long_message_forward: bool = False
    """是否启用长消息转发功能, 开启后会将发送的长文本消息拆分为多条消息发送, 以解决部分平台不支持发送长文本的问题"""

    qq_markdown: bool = True
    """是否启用QQ Markdown功能, 开启后会将发送的消息转换为 QQ Markdown 格式发送"""


cfg = plugin_config(CoreConfig)
