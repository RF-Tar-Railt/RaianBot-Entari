from __future__ import annotations

import random
from pathlib import Path

import diro
import ujson

root = Path(__file__).parent / "assets"

with (root / "public_deck.json").open("r", encoding="utf-8") as f:
    p_deck: dict[str, list[str]] = ujson.load(f)


def find_deck(name: str) -> int:
    if not name:
        return 0
    if name in p_deck:
        return 1
    return 2 if (name[0].isdigit() and len(name) < 3) or name == "100" else 0


def deck_list() -> list[str]:
    return list(p_deck.keys())


def draw(key: str, cnt: int = 1) -> str:
    if not key:
        return ""  # TODO: draw_help
    if not find_deck(key):
        return f"未找到卡组{key}"
    pro = p_deck[key][:]
    res = []
    while cnt:
        res.append(draw_card(pro))
        if not pro:
            break
        cnt -= 1
    return "|".join(res)


def draw_expr(exp: str) -> str:
    tmp_list: dict[str, list[str]] = {}
    cnt = 0
    while (lq := exp.find("{", cnt)) > -1:
        if lq and exp[lq - 1] == "\\":
            # Unescape "\{" -> "{" and continue scanning from this position.
            exp = f"{exp[: lq - 1]}{exp[lq:]}"
            cnt = lq
            continue
        rq = exp.find("}", lq)
        if rq < 0:
            break
        tmp = exp[lq + 1 : rq]
        if tmp not in p_deck:
            cnt = rq + 1
            continue
        if tmp not in tmp_list or not tmp_list[tmp]:
            # Keep an expression-local deck copy to avoid repeats until exhausted.
            tmp_list[tmp] = p_deck[tmp][:]
        res = draw_card(tmp_list[tmp])
        exp = f"{exp[:lq]}{res}{exp[rq + 1 :]}"
        cnt = lq + len(res)
    cnt = 0
    while (lq := exp.find("[", cnt)) > -1:
        if lq and exp[lq - 1] == "\\":
            # Unescape "\[" -> "[" and continue scanning from this position.
            exp = f"{exp[: lq - 1]}{exp[lq:]}"
            cnt = lq
            continue
        rq = exp.find("]", lq)
        if rq < 0:
            break
        roll = exp[lq + 1 : rq]
        cnt = rq + 1
        try:
            rd = diro.parse(roll)
        except ValueError:
            continue
        rd.roll()
        calc_res = str(rd.calc())
        exp = f"{exp[:lq]}{calc_res}{exp[rq + 1 :]}"
        cnt = lq + len(calc_res)
    return exp


def draw_card(tmp: list[str], is_back: bool = False) -> str:
    if not tmp:
        return ""
    index = 0 if len(tmp) == 1 else random.randrange(len(tmp))
    reply = tmp[index]
    if not is_back:
        tmp.pop(index)
    return draw_expr(reply)
