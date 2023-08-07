from __future__ import annotations

from netmiko import ConnectHandler


P_MAP = {
    'junos': ('juniper_junos', 'juniper_junos_telnet', 'show configuration | display inheritance no-comments'),
    'ios': ('cisco_ios', 'cisco_ios_telnet', 'show running-config'),
    'eos': ('arista_eos', 'arista_eos_telnet', 'show running-config'),
    'nxos': ('cisco_nxos', 'cisco_ios_telnet', 'show running-config'),
}

class NetLoader:
    __slots__ = (
        '__data',
    )

    @property
    def data(self) -> list[str]:
        return self.__data

    def __init__(self, host: str, port: int, username: str, password: str, proto: int, platform: str) -> None:
        if platform not in P_MAP:
            raise ValueError(f'The "{platform}" is not supported.')
        if proto not in (0, 1):
            raise ValueError('This protocol is not supported!')
        if not username or not password or not host or not port:
            raise ValueError('All the fields must be set!')
        self.__data: list[str] = []
        conn = ConnectHandler(
            device_type=P_MAP[platform][proto],
            host=host,
            port=port,
            username=username,
            password=password,
        )
        command = P_MAP[platform][2]
        result = conn.send_command(command)
        if not result:
            raise Exception('Network has returned an empty result.')
        for line in result.split('\n'):
            self.__data.append(line + '\n')
