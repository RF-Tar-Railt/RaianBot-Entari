import inspect
from datetime import datetime

from arclet.entari import Image, MessageChain, command, keeping, metadata, plugin
from arclet.entari.event.lifespan import AccountUpdate
from jinja2 import Environment
from jinja2.meta import find_undeclared_variables
from satori import LoginStatus

from entari_plugin_browser import text2img


from .config import StatusConfig
from .data import (
    CURRENT_TIMEZONE,
    get_cpu_count,
    get_cpu_status,
    get_disk_usage,
    get_memory_status,
    get_pid,
    get_python_version,
    get_swap_status,
    get_system_version,
    get_uptime,
    per_cpu_status,
)
from .helpers import humanize_date, humanize_delta, relative_time


metadata(name="状态", author=[{"name": "RF-Tar-Railt", "email": "rf_tar_railt@qq.com"}], config=StatusConfig)

# bot status
_run_time: datetime = keeping("run_time_start", datetime.now(CURRENT_TIMEZONE))
_connect_time: dict[str, datetime] = keeping("connect_time", {})


@plugin.listen(AccountUpdate)
async def record_time(event: AccountUpdate):
    if event.status is LoginStatus.ONLINE:
        _connect_time[f"{event.account.platform}_{event.account.self_id}"] = datetime.now(CURRENT_TIMEZONE)
    elif event.status in {LoginStatus.OFFLINE, LoginStatus.DISCONNECT}:
        _connect_time.pop(f"{event.account.platform}_{event.account.self_id}", None)


def get_run_time() -> datetime:
    """Get the time when NoneBot started running."""
    return _run_time


def get_connect_time() -> dict[str, datetime]:
    """Get the time when the bot connected to the server."""
    return _connect_time


cfg = plugin.get_config(StatusConfig)


_ev = Environment(trim_blocks=True, lstrip_blocks=True, autoescape=True, enable_async=True)
_ev.globals["relative_time"] = relative_time
_ev.filters["relative_time"] = relative_time
_ev.filters["humanize_date"] = humanize_date
_ev.globals["humanize_date"] = humanize_date
_ev.filters["humanize_delta"] = humanize_delta
_ev.globals["humanize_delta"] = humanize_delta

_t_ast = _ev.parse(cfg.template)
_t_vars = find_undeclared_variables(_t_ast)
_t = _ev.from_string(_t_ast)

KNOWN_VARS = {
    "cpu_count": get_cpu_count,
    "cpu_usage": get_cpu_status,
    "per_cpu_usage": per_cpu_status,
    "memory_usage": get_memory_status,
    "swap_usage": get_swap_status,
    "disk_usage": get_disk_usage,
    "uptime": get_uptime,
    "runtime": get_run_time,
    "connect_time": get_connect_time,
    "python_version": get_python_version,
    "system_version": get_system_version,
    "pid": get_pid,
}


async def _solve_required_vars() -> dict:
    """Solve required variables for template rendering."""
    return (
        {k: await v() if inspect.iscoroutinefunction(v) else v() for k, v in KNOWN_VARS.items() if k in _t_vars}
        if cfg.truncate
        else {k: await v() if inspect.iscoroutinefunction(v) else v() for k, v in KNOWN_VARS.items()}
    )


async def render_template() -> str:
    """Render status template with required variables."""
    message = await _t.render_async(**(await _solve_required_vars()))
    return message.strip("\n")


# @alcommand(cmd, post=True, send_error=True)
# @exclusive
# @accessable


@command.on("status")
async def status():
    text = await render_template()
    return MessageChain(Image.of(raw=await text2img(text)))
