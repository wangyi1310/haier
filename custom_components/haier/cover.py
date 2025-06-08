import logging
from homeassistant.components.cover import CoverEntity,CoverEntityFeature;
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import UnitOfTemperature, Platform
from . import async_register_entity
from .core.attribute import HaierAttribute
from .core.device import HaierDevice
from .entity import HaierAbstractEntity
from .helpers import try_read_as_bool

_LOGGER = logging.getLogger(__name__)
# 定义遮阳帘设备
# 1.使用setup构建设备实体（HaierCover） hass configEntry async_add_entities
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    # 注册一个实体
    await async_register_entity(
        hass,
        entry,
        async_add_entities,
        Platform.COVER,
        lambda device, attribute: HaierCover(device, attribute)
    )

#定义设备的实体基于HaierAbstractEntity和CoverEntity构建，提供了现成设备实体方法
class HaierCover(HaierAbstractEntity, CoverEntity):
    def __init__(self, device: HaierDevice, attribute: HaierAttribute):
        super().__init__(device, attribute)

    def _update_value(self):
        self._attr_is_closed = try_read_as_bool(self._attributes_data['onOffStatus'])
        self._attr_current_cover_position = int(self._attributes_data['openDegree'])
        
    # 打开窗帘
    def open_cover(self, **kwargs) -> None:
        _LOGGER.debug("执行窗帘打开")
        self._send_command({
            'onOffStatus': True
        })

    def close_cover(self, **kwargs) -> None:
        _LOGGER.debug("执行窗帘关闭")
        self._send_command({
            'onOffStatus': False
        })

    def stop_cover(self, **kwargs) -> None:
        _LOGGER.debug("执行窗帘暂停")
        self._send_command({
            'pause': True
        })

    def set_cover_position(self,position: int) -> None:
        _LOGGER.debug("执行设置窗帘开合度")
        self._send_command({
            'openDegree': position
        })