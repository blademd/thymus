from __future__ import annotations

import os
import json

from abc import ABC
from collections.abc import Iterator
from typing import Any


from thymus.contexts import Context, JunosContext, IOSContext, NXOSContext, EOSContext, XROSContext
from thymus.settings import Setting, IntSetting, StrSetting, BoolSetting


class PlatformLoadFail(Exception): ...


class PlatfromDumpFail(Exception): ...


class Platform(ABC):
    def __init__(self, path: str, *, load=False) -> None:
        self.link_context = Context
        self.settings: dict[str, Setting] = {
            'full_name': StrSetting('', read_only=True),
            'short_name': StrSetting('', read_only=True),
            'device_type': StrSetting('', read_only=True),
            'spaces': IntSetting(1, fixed_values=(1, 2, 4), pass_through=True),
            'up_limit': IntSetting(8, val_range=(1, 16), pass_through=True),
            'alias_command_show': StrSetting('show', max_length=8, empty=False, pass_through=True),
            'alias_command_go': StrSetting('go', max_length=8, empty=False, pass_through=True),
            'alias_command_top': StrSetting('top', max_length=8, empty=False, pass_through=True),
            'alias_command_up': StrSetting('up', max_length=8, empty=False, pass_through=True),
            'alias_sub_command_filter': StrSetting('filter', max_length=8, empty=False, pass_through=True),
            'alias_sub_command_wildcard': StrSetting('wildcard', max_length=8, empty=False, pass_through=True),
            'alias_sub_command_stubs': StrSetting('stubs', max_length=8, empty=False, pass_through=True),
            'alias_sub_command_sections': StrSetting('sections', max_length=8, empty=False, pass_through=True),
            'alias_sub_command_save': StrSetting('save', max_length=8, empty=False, pass_through=True),
            'alias_sub_command_diff': StrSetting('diff', max_length=8, empty=False, pass_through=True),
            'alias_sub_command_contains': StrSetting('contains', max_length=8, empty=False, pass_through=True),
            'alias_sub_command_count': StrSetting('count', max_length=8, empty=False, pass_through=True),
            'alias_sub_command_inactive': StrSetting('inactive', max_length=8, empty=False, pass_through=True),
            'alias_sub_command_reveal': StrSetting('reveal', max_length=8, empty=False, pass_through=True),
        }
        self.path = path
        if load:
            self.load()

    def __iter__(self) -> Iterator[tuple[str, Setting]]:
        yield from self.settings.items()

    def __getitem__(self, key: str) -> Setting:
        return self.settings[key]

    def __repr__(self) -> str:
        r = f"Full name:\t{self.settings['full_name'].value}\n"
        r += f"Short name:\t{self.settings['short_name'].value}\n"
        r += f"Device type:\t{self.settings['device_type'].value}\n"
        r += f"Spaces:\t\t{self.settings['spaces'].value}\n"
        r += f"Up depth limit:\t{self.settings['up_limit'].value}\n"
        return r

    def dump(self) -> None:
        try:
            with open(self.path, 'w', encoding='utf-8') as f:
                data: dict[str, Any] = {}
                for k, v in self.settings.items():
                    if v.read_only:
                        continue
                    data[k] = v.value
                json.dump(data, f, indent=4)
                f.flush()
                os.fsync(f.fileno())

        except Exception as error:
            raise PlatfromDumpFail(error)

    def load(self) -> None:
        try:
            with open(self.path, encoding='utf-8') as f:
                data: dict = json.load(f)
                for k, v in self.settings.items():
                    if v.read_only:
                        continue
                    if (value := data.get(k)) is not None:
                        v.value = value

        except Exception as error:
            raise PlatformLoadFail(error)


class JUNOS(Platform):
    def __init__(self, path: str, *, load=False) -> None:
        super().__init__(path, load=load)
        self.link_context = JunosContext
        self.settings['full_name'].value = 'Juniper JunOS'
        self.settings['short_name'].value = 'JunOS'
        self.settings['device_type'].value = 'juniper_junos'
        self.settings['spaces'].value = 2
        self.settings['alias_sub_command_filter'].value = 'match'
        self.settings['alias_sub_command_wildcard'].value = 'wc'
        self.settings['alias_sub_command_diff'].value = 'compare'


class IOS(Platform):
    def __init__(self, path: str, *, load=False) -> None:
        super().__init__(path, load=load)
        self.link_context = IOSContext
        self.settings['full_name'].value = 'Cisco IOS'
        self.settings['short_name'].value = 'IOS'
        self.settings['device_type'].value = 'cisco_ios'
        self.settings['base_heuristics'] = BoolSetting(True, pass_through=True)
        self.settings['heuristics'] = BoolSetting(False, pass_through=True)
        self.settings['crop'] = BoolSetting(False, pass_through=True)
        self.settings['promisc'] = BoolSetting(False, pass_through=True)
        self.settings['find_head'] = BoolSetting(False, pass_through=True)
        self.settings['alias_command_show'].value = 'show'
        self.settings['alias_command_go'].value = 'go'
        self.settings['alias_command_top'].value = 'end'
        self.settings['alias_command_up'].value = 'exit'
        self.settings['alias_sub_command_filter'].value = 'include'
        self.settings['alias_sub_command_stubs'].value = 'stubs'
        self.settings['alias_sub_command_sections'].value = 'sections'

    def __repr__(self) -> str:
        r = super().__repr__()
        r += f"{self.settings['full_name'].value} specifics:\n"
        r += f"Base Heuristics:\t{self.settings['base_heuristics'].value}\n"
        r += f"Heuristics:\t\t{self.settings['heuristics'].value}\n"
        r += f"Crop:\t\t\t{self.settings['crop'].value}\n"
        r += f"Promisc:\t\t{self.settings['promisc'].value}\n"
        r += f"Find head:\t\t{self.settings['find_head'].value}\n"
        return r


class NXOS(IOS):
    def __init__(self, path: str, *, load=False) -> None:
        super().__init__(path, load=load)
        self.link_context = NXOSContext
        self.settings['promisc'] = BoolSetting(True, pass_through=True, read_only=True)
        self.settings['full_name'].value = 'Cisco NX-OS'
        self.settings['short_name'].value = 'NX-OS'
        self.settings['device_type'].value = 'cisco_nxos'
        self.settings['spaces'].value = 2


class EOS(IOS):
    def __init__(self, path: str, *, load=False) -> None:
        super().__init__(path, load=load)
        self.link_context = EOSContext
        self.settings['promisc'] = BoolSetting(True, pass_through=True, read_only=True)
        self.settings['full_name'].value = 'Arista EOS'
        self.settings['short_name'].value = 'EOS'
        self.settings['device_type'].value = 'arista_eos'
        self.settings['spaces'].value = 2


class XROS(IOS):
    def __init__(self, path: str, *, load=False) -> None:
        super().__init__(path, load=load)
        self.link_context = XROSContext
        self.settings['promisc'] = BoolSetting(True, pass_through=True, read_only=True)
        self.settings['full_name'].value = 'Cisco XR-OS'
        self.settings['short_name'].value = 'XR-OS'
        self.settings['device_type'].value = 'cisco_xros'
        self.settings['spaces'].value = 2


PLATFORMS = (
    ('junos', JUNOS),
    ('ios', IOS),
    ('nxos', NXOS),
    ('eos', EOS),
    ('xros', XROS),
)
