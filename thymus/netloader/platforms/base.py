from __future__ import annotations

import asyncio
import asyncssh
import telnetlib3  # type: ignore
import re
import os

from typing import Literal, Optional, Sequence, TYPE_CHECKING
from abc import ABC, abstractmethod

from thymus.netloader.exceptions import (
    TimeoutError,
    DisconnectError,
    KeyError,
)

if TYPE_CHECKING:
    import logging

SSH_KEY_TYPES = (
    'ed25519_sk',
    'ecdsa_sk',
    'ed448',
    'ed25519',
    'ecdsa',
    'rsa',
    'dsa',
)


def read_keys_and_certs(passphrase: str = '', ignore_encrypted: bool = True) -> Sequence[asyncssh.SSHKeyPair]:
    """
    Replacement for asyncssh.load_default_keypairs(). This function covers a wider scope of filenames.
    """
    keys: list[asyncssh.SSHKey] = []
    certs: list[asyncssh.SSHCertificate] = []
    for folder in ('~/ssh/', '~/.ssh/'):
        path = os.path.expanduser(folder)
        if not os.path.isdir(path):
            continue
        for elem in os.listdir(path):
            for ktype in SSH_KEY_TYPES:
                if ktype in elem.lower():
                    try:
                        if 'pub' in elem.lower():
                            pub_key = asyncssh.read_public_key(os.path.join(path, elem))
                            keys.append(pub_key)
                        elif 'cert' in elem.lower():
                            cert = asyncssh.read_certificate(os.path.join(path, elem))
                            certs.append(cert)
                        else:
                            p_key = asyncssh.read_private_key(os.path.join(path, elem), passphrase)
                            keys.append(p_key)
                    except Exception:
                        pass
    return asyncssh.load_keypairs(
        keylist=keys, passphrase=passphrase, certlist=certs, ignore_encrypted=ignore_encrypted
    )


class Base(ABC):
    __slots__ = (
        '_host',
        '_port',
        '_username',
        '_password',
        '_connect_params',
        '_protocol',
        '_timeout',
        '_logger',
        '_conn',
        '_stdin',
        '_stdout',
        '_buf_limit',
        '_base_prompt',
        '_base_pattern',
    )

    _terminating_symbols = ['>', '#']
    _fetch_command = ''
    _no_paging_command = ''
    _pattern = ''

    @property
    def trailer(self) -> str:
        return f'{self._host}:{self._port} [{self._protocol}]'

    @property
    def terminating_line(self) -> str:
        return r'|'.join(map(re.escape, type(self)._terminating_symbols))

    def __init__(
        self,
        *,
        host: str,
        protocol: Literal['ssh', 'telnet'] = 'ssh',
        username: str = '',
        password: str = '',
        passphrase: str = '',
        port: int = -1,
        timeout: float = 15.0,
        logger: logging.Logger,
    ) -> None:
        if not host:
            raise ValueError('Host must be present.')
        if protocol not in ('ssh', 'telnet'):
            if protocol:
                raise ValueError(f'Unsupported protocol type: {protocol}.')
            else:
                raise ValueError('Protocol must be present.')
        if protocol == 'ssh' and not username:
            raise ValueError('Username for SSH protocol must be present.')
        if port == -1:
            port = 22 if protocol == 'ssh' else 23
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._connect_params = {
            'host': host,
            'port': port,
        }
        if protocol == 'ssh':
            if os.name == 'nt':
                # HACK
                # AsyncSSH under Windows uses only ssh-ed25519 which is not enough for legacy hosts.
                # So, I added ssh-rsa here, but this part requires testing.
                # At the moment, there is absolutely no desire to rewrite a stock function by adding ssh-rsa there.
                self._connect_params['server_host_key_algs'] = ('ssh-ed25519', 'ssh-rsa')
            if password:
                self._connect_params.update(
                    {
                        'username': username,
                        'password': password,
                    }
                )
            else:
                self._connect_params.update(
                    {
                        'username': username,
                        'client_keys': read_keys_and_certs(passphrase=passphrase),
                    }
                )
        self._protocol = protocol
        self._timeout = timeout
        self._logger = logger
        self._conn: Optional[asyncssh.SSHClientConnection | telnetlib3.TelnetClient] = None
        self._stdin: Optional[asyncssh.SSHWriter | telnetlib3.TelnetWriter] = None
        self._stdout: Optional[asyncssh.SSHReader | telnetlib3.TelnetReader] = None
        self._buf_limit = 65535
        self._base_pattern = ''
        self._base_prompt = ''

    def send_data(self, data: str = '', verbose: bool = True) -> None:
        if not self._stdin:
            raise Exception(f'Writing channel is not available for {self.trailer}.')
        data_to_send = f'{data}\n'
        if verbose:
            self._logger.debug(f'Sending data: {repr(data_to_send)}.')
        else:
            self._logger.debug('Sending data: ******\\n.')
        self._stdin.write(data_to_send)

    async def connect(self) -> None:
        await self._establish_connection()
        if self._protocol == 'telnet':
            await self._telnet_login()
        await self._flush_data()
        await self._set_base_prompt()
        await self._disable_paging()

    async def disconnect(self) -> None:
        if not self._conn:
            return
        self._logger.debug(f'Disconnecting from {self.trailer}.')
        if type(self._conn) is asyncssh.SSHClientConnection:
            self._conn.close()
            await self._conn.wait_closed()
        elif type(self._conn) is telnetlib3.TelnetClient:
            self._conn.connection_lost(None)
        self._logger.info(f'Disconnected from {self.trailer}.')

    async def fetch_config(self) -> str:
        self._logger.debug(f'Fetching config for {self.trailer}.')
        self.send_data(type(self)._fetch_command)
        output = await self._read_until_pattern()
        output = self.normalize_lines(output)
        output = self.strip_command(output)
        output = self.strip_prompt(output, self._base_prompt)
        return output

    async def __aenter__(self) -> Base:
        await self.connect()
        return self

    async def __aexit__(self, *args, **kwargs) -> None:
        await self.disconnect()

    async def _read_until_pattern(self, pattern: str = '', re_flags: int = 0, verbose: bool = False) -> str:
        if not self._stdout:
            raise ValueError(f'Reading channel is not available for {self.trailer}.')
        if not pattern:
            pattern = self._base_pattern
        data = ''
        self._logger.debug(f'Reading until pattern: "{pattern}" ({self._base_pattern}) for {self.trailer}.')
        while True:
            fut = self._stdout.read(self._buf_limit)
            try:
                data += await asyncio.wait_for(fut, self._timeout)
            except asyncio.TimeoutError:
                raise TimeoutError(self._host)
            if verbose:
                self._logger.debug(f'Data: {repr(data)}.')
            if pattern == self._base_pattern:
                if re.search(pattern, data, re_flags) and re.search(self._base_prompt, data, re_flags):
                    return data
            else:
                if re.search(pattern, data, re_flags):
                    return data

    async def _find_prompt(self) -> str:
        self._logger.debug(f'Finding prompt for {self.trailer}.')
        self.send_data()
        prompt = await self._read_until_pattern(self.terminating_line)
        prompt = prompt.strip()
        if not prompt:
            raise ValueError(f'Unable to find prompt for {self.trailer}.')
        self._logger.debug(f'Prompt found: "{prompt}" for {self.trailer}.')
        return prompt

    async def _establish_connection(self) -> None:
        self._logger.debug(f'Establishing connection with {self.trailer}.')
        try:
            if self._protocol == 'ssh':
                ssh_fut = asyncssh.connect(**self._connect_params)
                self._conn = await asyncio.wait_for(ssh_fut, self._timeout)
                self._stdin, self._stdout, _ = await self._conn.open_session(term_type='vt100', term_size=(200, 24))
            elif self._protocol == 'telnet':
                telnet_fut = telnetlib3.open_connection(**self._connect_params, cols=200, rows=24)
                self._stdout, self._stdin = await asyncio.wait_for(telnet_fut, self._timeout)
                self._conn = self._stdin.protocol
        except asyncssh.HostKeyNotVerifiable as error:
            raise KeyError(self._host, error.code, error.reason)
        except asyncio.TimeoutError:
            raise TimeoutError(self._host)
        except asyncssh.DisconnectError as error:
            raise DisconnectError(self._host, error.code, error.reason, self._protocol)
        self._logger.info(f'Connection is established with {self.trailer}.')

    async def _flush_data(self) -> None:
        self._logger.debug(f'Flushing data for {self.trailer}.')
        f = await self._read_until_pattern(self.terminating_line)
        self._logger.debug(f'Flushed: {repr(f)}.')

    async def _disable_paging(self) -> None:
        self._logger.debug(f'Disabling paging for {self.trailer}.')
        self.send_data(type(self)._no_paging_command)
        f = await self._read_until_pattern(self._base_pattern)
        self._logger.debug(f'Flushed: {repr(f)}.')

    @abstractmethod
    async def _telnet_login(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def _set_base_prompt(self) -> None:
        raise NotImplementedError

    @staticmethod
    def strip_command(data: str) -> str:
        backspace_char = '\x08'
        output = data.replace(backspace_char, '') if backspace_char in data else data
        lines = output.splitlines()
        result = lines[1:]
        return '\n'.join(result)

    @staticmethod
    def strip_prompt(data: str, prompt: str) -> str:
        lines = data.splitlines()
        last = lines[-1]
        if prompt in last:
            return '\n'.join(lines[:-1])
        return data

    @staticmethod
    def normalize_lines(data: str) -> str:
        new_line = re.compile(r'(\r\r\n|\r\n|\n\r)')
        return new_line.sub('\n', data)
