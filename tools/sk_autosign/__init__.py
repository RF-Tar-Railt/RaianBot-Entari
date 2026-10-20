import hashlib
import hmac
import json
from datetime import datetime
from typing import Literal, Protocol, TypedDict
from urllib.parse import urlparse

import httpx

from .crypto import get_d_id


class SKAutoSignRecord(Protocol):
    id: int
    """用户 ID"""

    token: str
    """森空岛token"""

    cred_value: str
    """森空岛cred_value"""

    cred_token: str
    """森空岛cred_token"""


base_url = "https://zonai.skland.com/api/v1"
grant_code_url = "https://as.hypergryph.com/user/oauth2/v2/grant"
# 使用认证代码获得cred
cred_code_url = "https://zonai.skland.com/web/v1/user/auth/generate_cred_by_code"

skland_app_code = "4ca99fa6b56cc2ba"
web_app_code = "be36d44aa36bfb5b"


class Binding(TypedDict):
    uid: str
    channelMasterId: str
    nickName: str
    channelName: str


class Bindings(TypedDict):
    appCode: str
    bindingList: list[Binding]


class SklandAPI:
    _headers = {
        "User-Agent": "Skland/1.32.1 (com.hypergryph.skland; build:103201004; Android 33; ) Okhttp/4.11.0",
        "Accept-Encoding": "gzip",
        "Connection": "close",
    }

    _header_for_sign = {"platform": "", "timestamp": "", "dId": "", "vName": ""}

    def __init__(self):
        self.client = httpx.AsyncClient(verify=False, timeout=30)

    async def get_sign_header(
        self,
        cred_token: str,
        cred_cred: str,
        url: str,
        method: Literal["get", "post"],
        query_body: dict | None = None,
        use_did: bool = False,
    ) -> dict:
        """获取带sign请求头

        Args:
            cred_token: 认证凭据。
            cred_cred: 认证凭据。
            url: 请求 URL。
            method: 请求方法。
            query_body: POST 请求体。
            use_did: 是否获取并使用设备 ID 参与签名计算。
        """
        timestamp = int(datetime.now().timestamp()) - 1
        header_for_sign = {**self._header_for_sign}
        if use_did:
            header_for_sign["dId"] = await get_d_id()
        header_ca = {**header_for_sign, "timestamp": str(timestamp)}
        parsed_url = urlparse(url)
        if method == "post":
            query_params = json.dumps(query_body) if query_body is not None else ""
        else:
            query_params = parsed_url.query
        header_ca_str = json.dumps(
            {**header_for_sign, "timestamp": str(timestamp)},
            separators=(",", ":"),
        )
        secret = f"{parsed_url.path}{query_params}{timestamp}{header_ca_str}"
        hex_secret = hmac.new(cred_token.encode("utf-8"), secret.encode("utf-8"), hashlib.sha256).hexdigest()
        signature = hashlib.md5(hex_secret.encode("utf-8")).hexdigest()
        return {"cred": cred_cred, **self._headers, "sign": signature, **header_ca}

    async def get_binding(self, cred_token: str, cred_cred: str) -> list[Bindings]:
        """获取绑定的角色"""
        binding_url = f"{base_url}/game/player/binding"
        try:
            response = await self.client.get(
                binding_url,
                headers=await self.get_sign_header(cred_token, cred_cred, binding_url, method="get"),
            )
            if status := response.json().get("code"):
                if status == 10000:
                    raise RuntimeError(f"获取绑定角色失败：{response.json().get('message')}")
                elif status == 10002:
                    raise RuntimeError(f"获取绑定角色失败：{response.json().get('message')}")
                if status != 0:
                    raise RuntimeError(f"获取绑定角色失败：{response.json().get('message')}")
            return response.json()["data"]["list"]
        except httpx.HTTPError as e:
            raise RuntimeError(f"获取绑定角色失败: {e}")

    async def ark_sign(self, cred_token: str, cred_cred: str, uid: str, channel_master_id: str):
        """进行明日方舟签到"""
        body = {"uid": uid, "gameId": channel_master_id}
        json_body = json.dumps(body, ensure_ascii=False, separators=(", ", ": "), allow_nan=False)
        sign_url = f"{base_url}/game/attendance"
        headers = await self.get_sign_header(
            cred_token,
            cred_cred,
            sign_url,
            method="post",
            query_body=body,
        )
        try:
            response = await self.client.post(
                sign_url,
                headers={**headers, "Content-Type": "application/json"},
                content=json_body,
            )
            if status := response.json().get("code"):
                if status == 10000:
                    raise RuntimeError(f"角色 {uid} 签到失败：{response.json().get('message')}")
                elif status == 10002:
                    raise RuntimeError(f"角色 {uid} 签到失败：{response.json().get('message')}")
                elif status != 0:
                    raise RuntimeError(f"角色 {uid} 签到失败：{response.json().get('message')}")
        except httpx.HTTPError as e:
            raise RuntimeError(f"角色 {uid} 签到失败: {e}")
        return response.json()["data"]

    async def get_grant_code(self, token: str, grant_type: int) -> str:
        """
        获取认证代码或token。

        Args:
            token (str): 用户token
            grant_type (int): 授权类型。0 返回森空岛认证代码(code)，1 返回官网通行证token。

        Returns:
            str: grant_type 为 0 时返回森空岛认证代码(code)，grant_type 为 1 时返回官网通行证 token。
        """
        code = skland_app_code if grant_type == 0 else web_app_code
        response = await self.client.post(
            "https://as.hypergryph.com/user/oauth2/v2/grant",
            json={"appCode": code, "token": token, "type": grant_type},
            headers={**self._headers},
        )
        if status := response.json().get("status"):
            if status != 0:
                raise RuntimeError(f"使用token获得认证代码失败：{response.json().get('msg')}")
        return response.json()["data"]["code"] if grant_type == 0 else response.json()["data"]["token"]

    async def get_cred(self, grant_code: str) -> tuple[str, str]:
        response = await self.client.post(
            "https://zonai.skland.com/api/v1/user/auth/generate_cred_by_code",
            json={"code": grant_code, "kind": 1},
            headers={**self._headers, "dId": await get_d_id()},
        )
        resp = response.json()
        if resp["code"] != 0:
            raise RuntimeError(f"获得cred失败：{resp.get('message')}")
        return resp["data"]["cred"], resp["data"]["token"]

    async def refresh_cred_token(self, cred_value: str) -> str:
        refresh_url = "https://zonai.skland.com/api/v1/auth/refresh"
        try:
            response = await self.client.get(
                refresh_url,
                headers={**self._headers, "cred": cred_value},
            )
            response.raise_for_status()
            if status := response.json().get("status"):
                if status != 0:
                    raise RuntimeError(f"刷新token失败：{response.json().get('message')}")
            token = response.json().get("data").get("token")
            return token
        except httpx.HTTPError as e:
            raise RuntimeError(f"刷新token失败：{str(e)}")


async def bind(token: str):
    api = SklandAPI()
    try:
        grand_code = await api.get_grant_code(token, grant_type=0)
        cred_cred, cred_token = await api.get_cred(grand_code)
    except RuntimeError as e:
        raise RuntimeError(f"绑定失败：{str(e)}")
    return cred_cred, cred_token


async def sign(record: SKAutoSignRecord):
    api = SklandAPI()
    if not record.cred_token or not record.cred_value:
        try:
            grand_code = await api.get_grant_code(record.token, grant_type=0)
            cred_cred, cred_token = await api.get_cred(grand_code)
            record.cred_token = cred_token
            record.cred_value = cred_cred
        except RuntimeError as e:
            yield {"status": False, "text": str(e), "target": ""}
            return
    try:
        bindings = await api.get_binding(record.cred_token, record.cred_value)
    except RuntimeError as e:
        yield {"status": False, "text": str(e), "target": ""}
        return
    binding_list: list[Binding] = []
    for binding in bindings:
        if binding["appCode"] == "arknights":
            binding_list.extend(binding["bindingList"])
    if not binding_list:
        yield {"status": False, "text": f"{record.id} 未创建方舟账号", "target": ""}
        return
    for b in binding_list:
        drname = b["nickName"]
        server = b["channelName"]
        result = {}
        try:
            sign_result = await api.ark_sign(record.cred_token, record.cred_value, b["uid"], b["channelMasterId"])
            result["status"] = True
            result["target"] = b["uid"]
            result["text"] = f"{server}账号 {drname}(UID {b['uid']})签到成功\n"
            awards = sign_result.get("awards", [])
            for award in awards:
                result["text"] += "获得的奖励ID为：" + award.get("resource", {}).get("id", "") + "\n"
                result["text"] += (
                    "此次签到获得了"
                    + str(award.get("count", 0))
                    + "单位的"
                    + award.get("resource", {}).get("name", "")
                    + "("
                    + award.get("resource", {}).get("type", "")
                    + ")\n"
                )
                result["text"] += "奖励类型为：" + award.get("type", "") + "\n"
        except RuntimeError as e:
            result["status"] = False
            result["target"] = b["uid"]
            result["text"] = f"{server}账号 {drname}(UID {b['uid']})签到失败:\n" + str(e)
        yield result
