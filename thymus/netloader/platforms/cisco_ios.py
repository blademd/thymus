from __future__ import annotations

import re

from asyncio import TimeoutError

from thymus.netloader.platforms import Base


class CiscoIOS(Base):
    __slots__ = ('_secret',)
    _fetch_command = 'show running-config'
    _no_paging_command = 'terminal length 0'
    _enter_priv_command = 'enable'
    _pattern = r'{prompt}.*?(\(.*?\))?[{tl}]\s*$'
    _priv_check = '#\s*$'

    def __init__(self, *, secret: str = '', **kwargs) -> None:
        super().__init__(**kwargs)
        self._secret = secret

    async def connect(self) -> None:
        await self._establish_connection()
        if self._protocol == 'telnet':
            await self._telnet_login()
        await self._flush_data()
        await self._set_base_prompt()
        await self._enable_mode()
        await self._disable_paging()

    async def _telnet_login(self) -> None:
        if self._protocol != 'telnet':
            return
        self._logger.debug(f'Trying to login to {self.trailer}.')
        err_msg = f'Auth failed with {self.trailer}.'
        login_prompt = r'Username:\s*$'
        password_prompt = r'Password:\s*$'
        pattern = f'{login_prompt}|{password_prompt}|{self.terminating_line}'
        login_to_send = f'{self._username}\r'
        password_to_send = f'{self._password}\r'
        try:
            loops = 3
            while loops:
                data = await self._read_until_pattern(pattern)
                if re.search(login_prompt, data):
                    self.send_data(login_to_send)
                elif re.search(password_prompt, data):
                    self.send_data(password_to_send, verbose=False)
                elif re.search(self.terminating_line, data):
                    self.send_data()  # feed the stream with another prompt to be eaten by the flush method later
                    self._logger.info(f'Login successful to {self.trailer}.')
                    return
                loops -= 1
        except TimeoutError:
            raise Exception(err_msg)
        raise Exception(err_msg)

    async def _set_base_prompt(self) -> None:
        self._logger.debug(f'Setting base prompt for {self.trailer}.')
        prompt = await self._find_prompt()
        self._base_prompt = prompt[:-1]
        base_prompt = re.escape(self._base_prompt[:12])
        pattern = type(self)._pattern
        self._base_pattern = pattern.format(prompt=base_prompt, tl=self.terminating_line)
        self._logger.debug(f'Base prompt "{self._base_prompt}" for {self.trailer}.')
        self._logger.debug(f'Base pattern "{self._base_pattern}" for {self.trailer}.')

    async def _check_enable_mode(self) -> bool:
        self._logger.debug(f'Checking whether privilege mode is active for {self.trailer}.')
        self.send_data()
        data = await self._read_until_pattern()
        if re.search(type(self)._priv_check, data):
            return True
        return False

    async def _enable_mode(self) -> None:
        err_msg = f'Failed to turn privilege mode on for {self.trailer}.'
        if not await self._check_enable_mode():
            self._logger.debug(f'Privilege mode is turned off, trying to turn on for {self.trailer}.')
            self.send_data(type(self)._enter_priv_command)
            password_prompt = 'Password:\s*$'
            try:
                await self._read_until_pattern(password_prompt)
                self.send_data(self._secret, verbose=False)
                data = await self._read_until_pattern()
                self._logger.debug(f'Flushed: {repr(data)}.')
                if not await self._check_enable_mode():
                    raise Exception(err_msg)
            except TimeoutError:
                raise Exception(err_msg)
        self._logger.debug(f'Privilege mode is active for {self.trailer}.')
