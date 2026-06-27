from arclet.entari import metadata, requires
from .config import Config

requires("entari-plugin-database", "entari-plugin-broswer")

metadata(
    name="微博",
    author=[{"name": "RF-Tar-Railt", "email": "rf_tar_railt@qq.com"}],
    version="0.1.0",
    description="简易的微博功能插件, 包括微博动态、微博用户信息等功能",
    config=Config,
)

from . import main  # noqa: F401
