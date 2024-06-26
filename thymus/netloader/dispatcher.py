from __future__ import annotations

from thymus.netloader.platforms import (
    CiscoIOS,
    CiscoNXOS,
    JuniperJunOS,
    AristaEOS,
    Base,
)


MAP: dict[str, type[Base]] = {
    'cisco_ios': CiscoIOS,  # type: ignore
    'cisco_nxos': CiscoNXOS,  # type: ignore
    'juniper_junos': JuniperJunOS,  # type: ignore
    'arista_eos': AristaEOS,  # type: ignore
}


def create(**kwargs) -> Base:
    if 'device_type' not in kwargs or not kwargs['device_type']:
        raise KeyError('Device type must be present.')

    if kwargs['device_type'] not in MAP:
        raise ValueError(f'Unsupported device type: {kwargs["device_type"]}.')

    platform = MAP[kwargs['device_type']]
    kwargs.pop('device_type')

    return platform(**kwargs)
