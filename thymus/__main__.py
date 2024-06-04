from __future__ import annotations

from uuid import uuid4

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Label
from textual.containers import Vertical
from textual.events import Resize

from thymus import __version__ as app_ver
from thymus import LOGO

from thymus.settings import AppSettings
from thymus.modals import OpenScreen, OpenScreenResult, ErrorScreen, SettingsScreen, ContextListScreen
from thymus.working_screen import WorkingScreen


class Thymus(App):
    CSS_PATH = 'styles/main.css'
    BINDINGS = [
        Binding('ctrl+o', 'request_open', 'Open'),
        Binding('ctrl+l', 'request_switch', 'List screens'),
        Binding('ctrl+s', 'request_settings', 'Settings'),
        Binding('ctrl+c', 'request_quit', 'Quit'),
        Binding('ctrl+p', 'request_screenshot', 'Screenshot', show=False),
    ]

    def __init__(self) -> None:
        super().__init__()

        self.working_screens: list[WorkingScreen] = []
        self.app_settings = AppSettings()

        self.install_screen(OpenScreen(self.app_settings), name='open_screen')

    # COMPOSE

    def compose(self) -> ComposeResult:
        yield Footer()

        with Vertical(id='main-screen-logo', classes='logo'):
            yield Label(LOGO.format(app_ver))

    # ACTIONS

    def action_request_open(self) -> None:
        self.push_screen('open_screen', self.open_request_cb)

    def action_request_switch(self) -> None:
        self.push_screen(ContextListScreen(self.working_screens))

    def action_request_settings(self) -> None:
        try:
            self.get_screen('settings_screen')
        except KeyError:
            self.install_screen(SettingsScreen(self.app_settings), name='settings_screen')

        self.push_screen('settings_screen')

    def action_request_quit(self) -> None:
        from thymus.modals import QuitScreen

        self.app.push_screen(QuitScreen('Do you really want to close Thymus?'), self.on_quit_cb)

    def action_request_screenshot(self) -> None:
        from pathlib import Path

        try:
            path = Path(self.app_settings['wrapper_folder'].value).expanduser()
            path = path / Path(Path(self.app_settings['screens_folder'].value))

            self.save_screenshot(path=str(path))
        except Exception as error:
            self.app_settings.logger.error(f'Screenshot saving error.\n{error}')

    # EVENTS

    def on_ready(self) -> None:
        self.dark = self.app_settings['night_mode'].value

    def on_quit_cb(self, result: bool) -> None:
        if result:
            self.app.exit()

    def on_resize(self, event: Resize) -> None:
        try:
            for control in self.query(Vertical):
                if 'logo' in control.classes:
                    width = 55 if len(self.screen_stack) == 1 else 120

                    if event.virtual_size.width <= width:
                        if control.styles.display != 'none':
                            control.styles.display = 'none'
                    else:
                        if control.styles.display != 'block':
                            control.styles.display = 'block'
        except Exception:
            ...

    @on(WorkingScreen.FetchFailed)
    def on_fetch_config_failed(self, event: WorkingScreen.FetchFailed) -> None:
        self.app_settings.logger.error(event.reason)
        self.switch_screen(ErrorScreen(event.reason))
        self.uninstall_screen(event.uid)

    @on(WorkingScreen.Release)
    def on_working_screen_release(self, event: WorkingScreen.Release) -> None:
        platform = event.screen.platform_name.upper()
        source = event.screen.source
        path = event.screen.path
        err = bool(event.error)

        if source == 'local':
            line = f'File "{path}" [{platform}] closed.'
        else:
            line = f'Remote file "{path}" [{platform}] closed.'

        self.app_settings.logger.info(line)

        if err:
            self.app_settings.logger.error(f'Context was closed with the error: "{event.error}".')

        if event.screen in self.working_screens:
            self.working_screens.remove(event.screen)

        event.screen.on_release()

        if not err:
            # pop the current working screen which requested the release
            # if there is an error, it was switched by the error modal
            self.pop_screen()

        self.uninstall_screen(event.screen)

    def open_request_cb(self, data: OpenScreenResult) -> None:
        try:
            screen_uid = str(uuid4())

            working_screen = WorkingScreen(data=data, name=screen_uid, settings=self.app_settings)
            self.install_screen(screen=working_screen, name=screen_uid)
        except Exception as err:
            err_msg = f'Error has occurred: {err}'
            self.app_settings.logger.error(err_msg)

            self.push_screen(ErrorScreen(err_msg))
            self.uninstall_screen(screen_uid)
        else:
            self.working_screens.append(working_screen)
            self.app_settings.update_last_opened_platform(data.platform)

            if len(self.screen_stack) == 1:
                self.push_screen(screen_uid)
            else:
                self.switch_screen(screen_uid)


if __name__ == '__main__':
    Thymus().run()
