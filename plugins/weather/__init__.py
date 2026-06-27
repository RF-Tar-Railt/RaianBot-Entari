from __future__ import annotations

import arclet.entari.config.models.pyd  # noqa: F401
from arclet.alconna import Alconna, Args, CommandMeta, Field
from arclet.entari import Image, MessageChain, metadata, plugin, command, local_data, Session

from entari_plugin_browser import playwright_api
from entari_plugin_llm import LLMToolEvent

from tools.heweather import CityNotFoundError, HeWeather, render
from tools.heweather.data import QWeatherConfig

metadata(
    name="天气查询",
    author=[{"name": "RF-Tar-Railt", "email": "rf_tar_railt@qq.com"}],
    version="0.1.0",
    description="和风天气",
    config=QWeatherConfig,
)

cmd = Alconna(
    "天气",
    Args["city?", str, Field(unmatch_tips=lambda x: f"请输入城市名字，而不是{x}")],
    meta=CommandMeta("查询某个城市的天气", example="$天气 北京\n$北京天气"),
)
# cmd.shortcut(
#     "(?P<city>.+)天气",
#     {
#         "fuzzy": False,
#         "prefix": True,
#         "command": "天气 {city}",
#         "humanized": "<城市>天气"
#     },
# )

weather_disp = command.mount(cmd, skip_for_unmatch=False).as_execute()

cfg = plugin.plugin_config(QWeatherConfig)


heweather = HeWeather(cfg)
hourlytype = cfg.hourlytype
cache_dir = local_data.get_cache_dir("weather")


@weather_disp.handle(label="天气")
async def weather(session: Session, city: command.Match[str]):
    """查询和风天气"""
    if city.available:
        city_name = city.result
    else:
        resp = await session.prompt("请输入地点名称：\n如 [回复机器人] 北京", timeout=30)
        if not resp:
            return
        city_name = resp.extract_plain_text()
    try:
        data = await heweather.load_data(city_name)
    except CityNotFoundError:
        return "地点是...空气吗?? >_<"
    file = cache_dir / f"{data.city_id}.html"
    with file.open("w+", encoding="utf-8") as f:
        f.write(await render(data, hourlytype))

    async with playwright_api.page(viewport={"width": 1000, "height": 300}, device_scale_factor=2) as page:
        await page.goto(file.absolute().as_uri())
        img = await page.screenshot(type="jpeg", quality=80, full_page=True, scale="device")
    return MessageChain(Image.of(raw=img, mime="image/jpeg"))


tools = plugin.dispatch(LLMToolEvent)


@tools
async def query_weather(city_name: str):
    """获取指定城市的天气信息

    如果用户未给出指定城市名称，需要询问用户

    Args:
        city_name: 城市名

    Returns:
        str | dict: 结构化 json 数据
    """
    try:
        data = await heweather.load_data(city_name)
    except CityNotFoundError:
        return "地点是...空气吗?? >_<"
    return data.model_dump()
