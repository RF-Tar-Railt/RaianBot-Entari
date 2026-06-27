from arclet.entari import BaseEvent, register_internal_event, attr


class NudgeEvent(BaseEvent):
    sender_id: int
    group_id: int
    target_id: int


class NudgeOnebotEvent(NudgeEvent):
    type = "nudge/onebot"

    sender_id = attr("user_id", int, internal=True)
    group_id = attr("group_id", int, internal=True)
    target_id = attr(int, internal=True)


class NudgeMilkyEvent(NudgeEvent):
    type = "nudge/milky"

    sender_id = attr(int, internal=True)
    group_id = attr(int, internal=True)
    target_id = attr("receiver_id", int, internal=True)


@register_internal_event
def _(t, typ, data):
    if t == "notice" and typ == "onebot" and data.get("sub_type") == "poke":
        return NudgeOnebotEvent
    elif typ == "notice.notify.poke":
        return NudgeOnebotEvent
    elif typ == "group_nudge":
        return NudgeMilkyEvent
