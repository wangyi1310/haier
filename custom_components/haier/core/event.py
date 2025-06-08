from typing import Callable, Coroutine, Any

from homeassistant.core import HomeAssistant, CALLBACK_TYPE, Event

from custom_components.haier import DOMAIN

# 定义设备控制事件名称
EVENT_DEVICE_CONTROL = 'device_control'
# 定义设备数据变更事件名称
EVENT_DEVICE_DATA_CHANGED = 'device_data_changed'
# 定义网关状态变更事件名称
EVENT_GATEWAY_STATUS_CHANGED = 'gateway_status_changed'


def wrap_event(name: str) -> str:
    """
    为事件名称添加域名前缀，确保事件名称的唯一性。

    :param name: 原始事件名称
    :return: 添加前缀后的完整事件名称
    """
    return '{}_{}'.format(DOMAIN, name)

# 为总线事件添加前缀，发布事件时使用
def fire_event(hass: HomeAssistant, event: str, data: dict) -> None:
    """
    在 Home Assistant 的事件总线上触发一个经过包装的事件。

    :param hass: Home Assistant 实例
    :param event: 原始事件名称
    :param data: 随事件一起传递的数据
    """
    #wrap_event 函数会给原始事件名称添加域名前缀，以此保证事件名称的唯一性。以下是 wrap_event 函数的代码：
    hass.bus.fire(wrap_event(event), data)

# 监听总线事件
def listen_event(
        hass: HomeAssistant,
        event: str,
        callback: Callable[[Event], Coroutine[Any, Any, None] | None]
) -> CALLBACK_TYPE:
    return hass.bus.async_listen(wrap_event(event), callback)
