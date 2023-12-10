from __future__ import annotations

import logging

from abc import ABC, abstractmethod

from ..contexts import (
    Context,
    JunOSContext,
    IOSContext,
    EOSContext,
    NXOSContext,
)


class Platform(ABC):
    __slots__ = ('_logger',)
    settings: dict[str, str | int] = {}
    context = Context
    current_settings: dict[str, str | int] = {}
    full_name = ''
    short_name = ''
    device_type = ''
    # show_command = ''
    # netmiko_ssh_class = ''
    # netmiko_telnet_class = ''

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger
        self.current_settings = self.settings

    @abstractmethod
    def validate(self, key: str, value: str | int) -> str | int:
        raise NotImplementedError


class JunosPlatform(Platform):
    settings = {
        'spaces': 2,
    }
    context: type[Context] = JunOSContext
    # show_command = 'show configuration | display inheritance no-comments'
    full_name = 'Juniper JunOS'
    short_name = 'JunOS'
    device_type = 'juniper_junos'
    # netmiko_ssh_class = 'juniper_junos'
    # netmiko_telnet_class = 'juniper_junos_telnet'

    def validate(self, key: str, value: str | int) -> str | int:
        if key == 'spaces':
            value = int(value)
            if value <= 0:
                raise Exception
        else:
            self._logger.warning(f'Unknown {self.short_name} attribute: {key}. Ignore.')
        return value


class IOSPlatform(Platform):
    settings: dict[str, str | int] = {
        'spaces': 1,
        'heuristics': 'off',
        'base_heuristics': 'on',
        'crop': 'off',
        'promisc': 'off',
    }
    context: type[Context] = IOSContext
    full_name = 'Cisco IOS'
    short_name = 'IOS'
    device_type = 'cisco_ios'
    # show_command = 'show running-config'
    # netmiko_ssh_class = 'cisco_ios'
    # netmiko_telnet_class = 'cisco_ios_telnet'

    def validate(self, key: str, value: str | int) -> str | int:
        if key == 'spaces':
            value = int(value)
            if value <= 0:
                raise Exception
        elif key in ('heuristics', 'crop', 'promisc', 'base_heuristics'):
            if value not in ('0', '1', 'on', 'off', 0, 1):
                raise Exception
        else:
            self._logger.warning(f'Unknown {self.short_name} attribute: {key}. Ignore.')
        return value


class NXOSPlatform(Platform):
    settings: dict[str, str | int] = {
        'spaces': 2,
        'heuristics': 'off',
        'base_heuristics': 'on',
        'crop': 'off',
    }
    context: type[Context] = NXOSContext
    full_name = 'Cisco NX-OS'
    short_name = 'NXOS'
    device_type = 'cisco_nxos'
    # show_command = 'show running-config'
    # netmiko_ssh_class = 'cisco_nxos'
    # netmiko_telnet_class = 'cisco_ios_telnet'

    def validate(self, key: str, value: str | int) -> str | int:
        if key == 'spaces':
            value = int(value)
            if value <= 0:
                raise Exception
        elif key in ('heuristics', 'crop', 'base_heuristics'):
            if value not in ('0', '1', 'on', 'off', 0, 1):
                raise Exception
        else:
            self._logger.warning(f'Unknown {self.short_name} attribute: {key}. Ignore.')
        return value


class EOSPlatform(Platform):
    settings: dict[str, str | int] = {
        'spaces': 2,
        'heuristics': 'off',
        'base_heuristics': 'on',
        'crop': 'off',
        'promisc': 'off',
    }
    context: type[Context] = EOSContext
    full_name = 'Arista EOS'
    short_name = 'EOS'
    device_type = 'arista_eos'
    # show_command = 'show running-config'
    # netmiko_ssh_class = 'arista_eos'
    # netmiko_telnet_class = 'arista_eos_telnet'

    def validate(self, key: str, value: str | int) -> str | int:
        if key == 'spaces':
            value = int(value)
            if value <= 0:
                raise Exception
        elif key in ('heuristics', 'crop', 'promisc', 'base_heuristics'):
            if value not in ('0', '1', 'on', 'off', 0, 1):
                raise Exception
        else:
            self._logger.warning(f'Unknown {self.short_name} attribute: {key}. Ignore.')
        return value
