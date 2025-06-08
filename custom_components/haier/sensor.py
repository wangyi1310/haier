import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from . import async_register_entity
from .core.attribute import HaierAttribute
from .core.device import HaierDevice
from .entity import HaierAbstractEntity

_LOGGER = logging.getLogger(__name__)

# 设置传感器实体
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    await async_register_entity(
        hass,
        entry,
        async_add_entities,
        Platform.SENSOR,
        lambda device, attribute: HaierSensor(device, attribute)
    )


class HaierSensor(HaierAbstractEntity, SensorEntity):

    def __init__(self, device: HaierDevice, attribute: HaierAttribute):
        super().__init__(device, attribute)

    #更新实体上的数值
    def _update_value(self):
        comparison_table = self._attribute.ext.get('value_comparison_table', {})

        value = self._attributes_data[self._attribute.key]
        self._attr_native_value = comparison_table[value] if value in comparison_table else value





