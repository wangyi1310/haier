import logging
from abc import ABC, abstractmethod

from homeassistant.core import Event
from homeassistant.helpers.entity import DeviceInfo, Entity

from . import DOMAIN
from .core.attribute import HaierAttribute
from .core.event import EVENT_DEVICE_DATA_CHANGED, EVENT_GATEWAY_STATUS_CHANGED, EVENT_DEVICE_CONTROL
from .core.device import HaierDevice
from .core.event import listen_event, fire_event

_LOGGER = logging.getLogger(__name__)

#定义海尔entry实体，集成Ha的Entry和ABC
class HaierAbstractEntity(Entity, ABC):

    _device: HaierDevice

    _attribute: HaierAttribute

    def __init__(self, device: HaierDevice, attribute: HaierAttribute):
        self._attr_unique_id = '{}.{}_{}'.format(DOMAIN, device.id, attribute.key).lower()
        self.entity_id = self._attr_unique_id
        self._attr_should_poll = False

        # 将海尔设备转成DeviceInfo类型，保存到实体的Attr的device_info中
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.id.lower())},
            name=device.name,
            manufacturer='海尔',
            model=device.product_name
        )

        # 将自定义的attrubute转成实体的_attr_name
        self._attr_name = attribute.display_name
        for key, value in attribute.options.items():
            setattr(self, '_attr_' + key, value)

        # 设备保存到上中
        self._device = device
        self._attribute = attribute
        # 保存当前设备下所有attribute的数据
        self._attributes_data = {}
        # 取消监听回调
        self._listen_cancel = []

    # 定义发送命令的方法，在子类中实现具体的发送逻辑
    def _send_command(self, attributes):
        """
        发送控制命令
        :param attributes:
        :return:
        """
        # 触发操作一定会触发控制事件发生，然后会在事件循环中进行处理
        # 触发事件，通知设备数据变更，并传入设备id和属性数据，事件Loop中会获取事件然后进行处理
        fire_event(self.hass, EVENT_DEVICE_CONTROL, {
            'deviceId': self._device.id,
            'attributes': attributes
        })

    @abstractmethod
    def _update_value(self):
        pass
    
    # 实体添加到HA中时，当事件触发后会自动调用
    async def async_added_to_hass(self) -> None:
        # 事件触发后，回调设置状态
        def status_callback(event):
            self._attr_available = event.data['status']
            self.schedule_update_ha_state()

        self._listen_cancel.append(listen_event(self.hass, EVENT_GATEWAY_STATUS_CHANGED, status_callback))

        # 事件触发后，回调设置属性值
        def data_callback(event):
            if event.data['deviceId'] != self._device.id:
                return

            self._attributes_data = event.data['attributes']
            self._update_value()
            self.schedule_update_ha_state()
        #设置一个监听数据盖面的回调，并将添加到_listen_cancel中，方便取消监听
        self._listen_cancel.append(listen_event(self.hass, EVENT_DEVICE_DATA_CHANGED, data_callback))

        # 预先进行一次数据快照
        data_callback(Event('', data={
            'deviceId': self._device.id,
            'attributes': self._device.attribute_snapshot_data
        }))

    #从HA中移除实体时，取消监听回调
    async def async_will_remove_from_hass(self) -> None:
        for cancel in self._listen_cancel:
            cancel()



