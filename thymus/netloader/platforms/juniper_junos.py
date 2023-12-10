from __future__ import annotations

import re

from asyncio import TimeoutError

from thymus.netloader.platforms.base import Base


class JuniperJunOS(Base):
    _terminating_symbols = ['>', '#', '%']
    _fetch_command = 'show configuration | display inheritance no-comments'
    _no_paging_command = 'set cli screen-length 0'
    _enter_cli_command = 'cli'
    _pattern = r'\w+(\@[\-\w]*)?[{tl}]\s*$'
    _cli_check = r'>\s*$'

    async def connect(self) -> None:
        await self._establish_connection()
        if self._protocol == 'telnet':
            await self._telnet_login()
        await self._flush_data()
        await self._set_base_prompt()
        await self._cli_mode()
        await self._disable_paging()

    async def _telnet_login(self) -> None:
        if self._protocol != 'telnet':
            return
        self._logger.debug(f'Trying to login to {self.trailer}.')
        login_prompt = r'login:\s*$'
        password_prompt = r'Password:\s*$'
        login_to_send = f'{self._username}\r'
        password_to_send = f'{self._password}\r'
        try:
            await self._read_until_pattern(login_prompt)
            self.send_data(login_to_send)
            await self._read_until_pattern(password_prompt)
            self.send_data(password_to_send, verbose=False)
            await self._read_until_pattern(self.terminating_line)
        except TimeoutError:
            raise Exception(f'Auth failed with {self.trailer}.')
        self.send_data()  # feed the stream with another prompt to be eaten by the flush method later
        self._logger.info(f'Login successful to {self.trailer}.')

    async def _set_base_prompt(self) -> None:
        self._logger.debug(f'Setting base prompt for {self.trailer}.')
        prompt = await self._find_prompt()
        if '\n' in prompt:
            lines = prompt.splitlines()
            prompt = lines[-1]
        prompt = prompt[:-1]
        if '@' in prompt:
            prompt = prompt.split('@')[1]
        self._base_prompt = prompt
        pattern = type(self)._pattern
        self._base_pattern = pattern.format(tl=self.terminating_line)
        self._logger.debug(f'Base prompt "{self._base_prompt}" for {self.trailer}.')
        self._logger.debug(f'Base pattern "{self._base_pattern}" for {self.trailer}.')

    async def _check_cli_mode(self) -> bool:
        self._logger.debug(f'Checking whether CLI mode is active for {self.trailer}.')
        self.send_data()
        data = await self._read_until_pattern()
        if re.search(type(self)._cli_check, data):
            return True
        return False

    async def _cli_mode(self) -> None:
        if not await self._check_cli_mode():
            self._logger.debug(f'CLI mode is turned off, trying to turn on for {self.trailer}.')
            self.send_data(type(self)._enter_cli_command)
            data = await self._read_until_pattern()
            self._logger.debug(f'Flushed: {repr(data)}.')
            if not await self._check_cli_mode():
                raise Exception(f'Failed to turn CLI mode on for {self.trailer}.')
        self._logger.debug(f'CLI mode is active for {self.trailer}.')
