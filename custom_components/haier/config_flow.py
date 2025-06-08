import logging
import time
from typing import Any, Dict

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_TOKEN
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.config_validation import multi_select

from .const import DOMAIN, FILTER_TYPE_EXCLUDE, FILTER_TYPE_INCLUDE
from .core.client import HaierClientException, HaierClient
from .core.config import AccountConfig, DeviceFilterConfig, EntityFilterConfig

_LOGGER = logging.getLogger(__name__)

CLIENT_ID = 'client_id'
REFRESH_TOKEN = 'refresh_token'

class HaierConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """
    海尔集成的配置流程类，用于处理用户配置输入和创建配置条目。
    该类继承自 Home Assistant 的 ConfigFlow 类，负责引导用户完成海尔集成的配置过程，
    包括账号认证、设备筛选和实体筛选等步骤。
    """
    VERSION = 2

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """
        处理用户配置流程的第一步，收集用户输入的客户端 ID、刷新令牌和默认加载所有实体的选项。
        尝试使用用户提供的刷新令牌获取访问令牌和用户信息，若认证成功则创建配置条目；
        若认证失败则显示错误信息，提示用户重新输入。

        :param user_input: 用户输入的配置信息，包含客户端 ID、刷新令牌和默认加载所有实体的选项，可能为 None。
        :return: 一个 FlowResult 对象，根据处理结果返回不同的表单或配置条目。
        """
        errors: Dict[str, str] = {}
        if user_input is not None:
            try:
                # 根据refresh_token获取token
                client = HaierClient(self.hass, user_input[CLIENT_ID], '')
                token_info = await client.refresh_token(user_input[REFRESH_TOKEN])
                # 获取用户信息
                client = HaierClient(self.hass, user_input[CLIENT_ID], token_info.token)
                user_info = await client.get_user_info()
                
                # 创建一个配置的Entry
                return self.async_create_entry(title="Haier - {}".format(user_info['mobile']), data={
                    'account': {
                        'client_id': user_input[CLIENT_ID],
                        'token': token_info.token,
                        'refresh_token': token_info.refresh_token,
                        'expires_at': int(time.time()) + token_info.expires_in,
                        'default_load_all_entity': user_input['default_load_all_entity']
                    }
                })
            except HaierClientException as e:
                _LOGGER.warning(str(e))
                errors['base'] = 'auth_error'
        #如果用户的输入是空的，就展示一个表单给用户
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CLIENT_ID): str,
                    vol.Required(REFRESH_TOKEN): str,
                    vol.Required('default_load_all_entity', default=True): bool,
                }
            ),
            errors=errors
        )

    # 对已经存在的配置进行修改
    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        """
        获取配置选项流程的处理程序。

        :param config_entry: 现有的配置条目对象。
        :return: 一个 OptionsFlow 实例，用于处理配置选项的修改。
        """
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """
    处理海尔集成配置选项的流程类，允许用户修改账号设置、筛选设备和实体等配置。
    该类继承自 Home Assistant 的 OptionsFlow 类，提供多个步骤的配置选项修改界面。
    """
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """
        初始化 OptionsFlowHandler 实例。

        :param config_entry: 现有的配置条目对象，用于获取和保存配置信息。
        """
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """
        显示配置选项的功能菜单，让用户选择要进行的配置操作。

        :param user_input: 用户输入的配置信息，可能为 None。
        :return: 一个 FlowResult 对象，显示功能菜单表单。
        """
        return self.async_show_menu(
            step_id="init",
            menu_options=['account', 'device', 'entity_device_selector']
        )

    async def async_step_account(self,  user_input: dict[str, Any] | None = None) -> FlowResult:
        """
        处理账号设置的配置步骤，允许用户修改客户端 ID、刷新令牌和默认加载所有实体的选项。
        尝试使用用户提供的刷新令牌获取新的访问令牌和用户信息，若成功则保存配置并重新加载集成；
        若失败则显示错误信息。

        :param user_input: 用户输入的账号配置信息，可能为 None。
        :return: 一个 FlowResult 对象，根据处理结果返回不同的表单或配置条目。
        """
        errors: Dict[str, str] = {}

        # 将config_entry转成AccountConfig
        cfg = AccountConfig(self.hass, self.config_entry)

        if user_input is not None:
            try:
                # 根据refresh_token获取token
                client = HaierClient(self.hass, user_input[CLIENT_ID], '')
                token_info = await client.refresh_token(user_input[REFRESH_TOKEN])
                # 获取用户信息
                client = HaierClient(self.hass, user_input[CLIENT_ID], token_info.token)
                user_info = await client.get_user_info()

                cfg.client_id = user_input[CLIENT_ID]
                cfg.token = token_info.token
                cfg.refresh_token = token_info.refresh_token
                cfg.expires_at = int(time.time()) + token_info.expires_in
                cfg.default_load_all_entity = user_input['default_load_all_entity']
                # 保存配置到Entry中
                cfg.save(user_info['mobile'])

                await self.hass.config_entries.async_reload(self.config_entry.entry_id)
                return self.async_create_entry(title='', data={})
            except HaierClientException as e:
                _LOGGER.warning(str(e))
                errors['base'] = 'auth_error'
        # 更新完成之后chain展示表单数据
        return self.async_show_form(
            step_id="account",
            data_schema=vol.Schema(
                {
                    vol.Required(CLIENT_ID, default=cfg.client_id): str,
                    vol.Required(REFRESH_TOKEN, default=cfg.refresh_token): str,
                    vol.Required('default_load_all_entity', default=cfg.default_load_all_entity): bool,
                }
            ),
            errors=errors
        )
    # 决定哪些设备是否接入Ha
    async def async_step_device(self,  user_input: dict[str, Any] | None = None) -> FlowResult:
        """
        处理设备筛选的配置步骤，允许用户选择设备筛选类型（排除或包含）和目标设备。
        保存用户选择的筛选配置信息。

        :param user_input: 用户输入的设备筛选配置信息，可能为 None。
        :return: 一个 FlowResult 对象，根据处理结果返回不同的表单或配置条目。
        """
        cfg = DeviceFilterConfig(self.hass, self.config_entry)

        # 更新设备筛选
        if user_input is not None:
            cfg.set_filter_type(user_input['filter_type'])
            cfg.set_target_devices(user_input['target_devices'])
            cfg.save()

            return self.async_create_entry(title='', data={})

        devices = {}
        for item in self.hass.data[DOMAIN]['devices']:
            devices[item.id] = item.name

        return self.async_show_form(
            step_id="device",
            data_schema=vol.Schema(
                {
                    vol.Required('filter_type', default=cfg.filter_type): vol.In({
                        FILTER_TYPE_EXCLUDE: 'Exclude',
                        FILTER_TYPE_INCLUDE: 'Include',
                    }),
                    # 展示所有设备和选择生效的设备
                    vol.Optional('target_devices', default=cfg.target_devices): multi_select(devices)
                }
            )
        )

    # 实体按照设备处理

    async def async_step_entity_device_selector(self,  user_input: dict[str, Any] | None = None) -> FlowResult:
        """
        处理实体筛选的设备选择步骤，让用户选择要进行实体筛选的目标设备。
        保存用户选择的目标设备信息，并跳转到实体筛选步骤。

        :param user_input: 用户输入的目标设备信息，可能为 None。
        :return: 一个 FlowResult 对象，根据处理结果返回不同的表单或执行下一步操作。
        """
        if user_input is not None:
            self.hass.data[DOMAIN]['entity_filter_target_device'] = user_input['target_device']
            return await self.async_step_entity_filter()

        devices = {}
        for item in self.hass.data[DOMAIN]['devices']:
            devices[item.id] = item.name

        return self.async_show_form(
            step_id="entity_device_selector",
            data_schema=vol.Schema(
                {
                    vol.Required('target_device'): vol.In(devices)
                }
            )
        )

    async def async_step_entity_filter(self,  user_input: dict[str, Any] | None = None) -> FlowResult:
        """
        处理实体筛选的配置步骤，允许用户选择实体筛选类型（排除或包含）和目标实体。
        保存用户选择的实体筛选配置信息，并重新加载集成。

        :param user_input: 用户输入的实体筛选配置信息，可能为 None。
        :return: 一个 FlowResult 对象，根据处理结果返回不同的表单或配置条目。
        """
        cfg = EntityFilterConfig(self.hass, self.config_entry)

        if user_input is not None:
            cfg.set_filter_type(user_input['device_id'], user_input['filter_type'])
            cfg.set_target_entities(user_input['device_id'], user_input['target_entities'])
            cfg.save()

            await self.hass.config_entries.async_reload(self.config_entry.entry_id)

            return self.async_create_entry(title='', data={})

        target_device_id = self.hass.data[DOMAIN].pop('entity_filter_target_device', '')
        for device in self.hass.data[DOMAIN]['devices']:
            if device.id == target_device_id:
                target_device = device
                break
        else:
            raise ValueError('Device [{}] not found'.format(target_device_id))

        entities = {}
        for attribute in target_device.attributes:
            entities[attribute.key] = attribute.display_name

        filtered = [item for item in cfg.get_target_entities(target_device_id) if item in entities]

        return self.async_show_form(
            step_id="entity_filter",
            data_schema=vol.Schema(
                {
                    vol.Required('device_id', default=target_device_id): str,
                    vol.Required('filter_type', default=cfg.get_filter_type(target_device_id)): vol.In({
                        FILTER_TYPE_EXCLUDE: 'Exclude',
                        FILTER_TYPE_INCLUDE: 'Include',
                    }),
                    vol.Optional('target_entities', default=filtered): multi_select(
                        entities
                    )
                }
            )
        )

