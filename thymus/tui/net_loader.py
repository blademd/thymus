from __future__ import annotations

from netmiko import ConnectHandler  # type: ignore

from ..settings import Platform


class NetLoader:
    __slots__ = ('__data',)

    @property
    def data(self) -> list[str]:
        return self.__data

    def __init__(
        self,
        *,
        host: str,
        platform: Platform,
        port: int = 22,
        username: str = '',
        password: str = '',
        proto: int = 0,
    ) -> None:
        """
        `proto` - zero is for SSH, one is for Telnet.
        """
        if proto not in (0, 1):
            raise ValueError('This protocol is not supported!')
        self.__data: list[str] = []
        device_type = platform.netmiko_ssh_class if not proto else platform.netmiko_telnet_class
        conn = ConnectHandler(
            device_type=device_type,
            host=host,
            port=port,
            username=username,
            password=password,
            allow_agent=True,
            system_host_keys=True,
        )
        command = platform.show_command
        result = conn.send_command(command)
        if not result:
            raise Exception('Network has returned an empty result.')
        for line in result.split('\n'):
            self.__data.append(line + '\n')
        conn.disconnect()
