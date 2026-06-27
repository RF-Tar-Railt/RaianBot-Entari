from __future__ import annotations

import asyncio
from pydantic import BaseModel, model_validator
from httpx import URL, AsyncClient, Response
from loguru import logger

from .model import (
    AirApi,
    APIError,
    CityNotFoundError,
    ConfigError,
    DailyApi,
    HourlyApi,
    NowApi,
    QWeatherConfig,
    WarningApi,
)
from .utils import get_jwt_token


class HeWeatherData(BaseModel):
    name: str
    city_id: str
    now: NowApi
    daily: DailyApi
    air: AirApi
    warning: WarningApi | None
    hourly: HourlyApi

    @model_validator(mode="after")
    def check_api_response(cls, values):
        if isinstance(values, HeWeatherData):
            now, daily, air, warning = (
                values.now,
                values.daily,
                values.air,
                values.warning,
            )
        else:
            now = values.get("now")
            daily = values.get("daily")
            air = values.get("air")
            warning = values.get("warning")

        if now.code == "200" and daily.code == "200":
            return values
        else:
            raise APIError(
                "错误! 请检查配置! "
                f"错误代码: now: {now.code}  "
                f"daily: {daily.code}  "
                + "air: {}  ".format(air.code if air else "None")
                + "warning: {}".format(warning.code if warning else "None")
                + "\n请参考: https://dev.qweather.com/docs/start/status-code/"
            )


class HeWeather:
    def __url__(self):
        self.host = URL(self.config.apihost)
        # self.url_geoapi = "https://geoapi.qweather.com/v2/city/"
        # if self.api_type == 2 or self.api_type == 1:
        #     self.url_weather_api = "https://api.qweather.com/v7/weather/"
        #     self.url_weather_warning = "https://api.qweather.com/v7/warning/now"
        #     self.url_air = "https://api.qweather.com/v7/air/now"
        #     self.url_hourly = "https://api.qweather.com/v7/weather/24h"

        #     logger.info("使用标准订阅API")

        # elif self.api_type == 0:
        #     self.url_weather_api = "https://devapi.qweather.com/v7/weather/"
        #     self.url_weather_warning = "https://devapi.qweather.com/v7/warning/now"
        #     self.url_air = "https://devapi.qweather.com/v7/air/now"
        #     self.url_hourly = "https://devapi.qweather.com/v7/weather/24h"

        #     logger.info("使用免费订阅API")
        # else:
        #     raise ConfigError(
        #         "api_type 必须是为 (int)0 -> 免费订阅, "
        #         "(int)1 -> 标准订阅, (int)2 -> 商业版"
        #         f"\n当前为: ({type(self.api_type)}){self.api_type}"
        #     )

    def _forecast_days(self):
        self.forecast_days = self.config.forecase_days
        if self.forecast_days:
            if self.api_type == 0 and not (3 <= self.forecast_days <= 7):
                raise ConfigError("api_type = 0 免费订阅 预报天数必须 3<= x <=7")

    def __init__(self, config: QWeatherConfig, api_type: int = 0):
        self.config = config
        # self.apikey = api_key
        self.api_type = config.apitype
        self.__url__()

        self._forecast_days()

        # self.now: Optional[Dict[str, str]] = None
        # self.daily = None
        # self.air = None
        # self.warning = None
        self.__reference = "\n请参考: https://dev.qweather.com/docs/start/status-code/"

    async def load_data(self, city_name):
        city_id = await self._get_city_id(city_name)
        now, daily, air, warning, hourly = await asyncio.gather(
            self._now(city_id),
            self._daily(city_id),
            self._air(city_id),
            self._warning(city_id),
            self._hourly(city_id),
        )

        return HeWeatherData(
            name=city_name, city_id=city_id, now=now, daily=daily, air=air, warning=warning, hourly=hourly
        )

    async def _get_data(self, url: URL, params: dict) -> Response:
        headers = {}

        if self.config.apikey:
            headers = {"X-QW-Api-Key": self.config.apikey}

        if self.config.use_jwt and not self.config.apikey:
            headers = {
                "Authorization": f"Bearer {get_jwt_token(self.config)}",
            }

        if not headers:
            raise ConfigError("请确保已经配置 apikey 或 jwt")

        async with AsyncClient() as client:
            res = await client.get(url, params=params, headers=headers)
        return res

    async def _get_city_id(self, city_name: str):
        url = self.host.join("/geo/v2/city/lookup")
        res = await self._get_data(
            url=url,
            params={"location": city_name, "number": 1},
        )

        res = res.json()

        if res["code"] == "404":
            raise CityNotFoundError()
        elif res["code"] != "200":
            raise APIError("错误! 错误代码: {}".format(res["code"]) + self.__reference)
        else:
            self.city_name = res["location"][0]["name"]
            return res["location"][0]["id"]

    def _check_response(self, response: Response) -> bool:
        if response.status_code == 200:
            logger.debug(f"{response.json()}")
            return True
        else:
            raise APIError(f"Response code:{response.status_code}")

    async def _now(self, city_id: str) -> NowApi:
        url = self.host.join("/v7/weather/now")
        res = await self._get_data(
            url=url,
            params={"location": city_id},
        )
        self._check_response(res)
        return NowApi(**res.json())

    async def _daily(self, city_id: str) -> DailyApi:
        url = self.host.join(f"/v7/weather/{self.forecast_days}d")
        res = await self._get_data(
            url=url,
            params={"location": city_id},
        )
        self._check_response(res)
        return DailyApi(**res.json())

    async def _air(self, city_id: str) -> AirApi:
        url = self.host.join("/v7/air/now")
        res = await self._get_data(
            url=url,
            params={"location": city_id},
        )
        self._check_response(res)
        return AirApi(**res.json())

    async def _warning(self, city_id: str) -> WarningApi | None:
        url = self.host.join("/v7/warning/now")
        res = await self._get_data(
            url=url,
            params={"location": city_id},
        )
        self._check_response(res)
        return None if res.json().get("code") == "204" else WarningApi(**res.json())

    async def _hourly(self, city_id: str) -> HourlyApi:
        url = self.host.join("/v7/weather/24h")
        res = await self._get_data(
            url=url,
            params={"location": city_id},
        )
        self._check_response(res)
        return HourlyApi(**res.json())
