from arclet.alconna import config as alconna_config
from arclet.alconna.tools.formatter import MarkdownTextFormatter
from arclet.entari import Entari

alconna_config.default_namespace.formatter_type = MarkdownTextFormatter

app = Entari.load("")
app.run()
