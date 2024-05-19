from __future__ import annotations

from logging.handlers import BufferingHandler

from textual import on
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import TabbedContent, TabPane, Label, RichLog, Collapsible, Select, Input, Switch, Rule
from textual.lazy import Lazy
from textual.validation import ValidationResult, Validator

from rich.text import Text
from rich.syntax import Syntax
from rich.highlighter import ReprHighlighter

from thymus import __version__ as app_ver
from thymus import LOGO, CODE_SAMPLE
from thymus.settings import AppSettings, Setting, IntSetting, StrSetting, BoolSetting


class SettingsValidator(Validator):
    def __init__(self, setting: Setting) -> None:
        self.setting = setting

    def validate(self, value: str) -> ValidationResult:
        try:
            if isinstance(self.setting, IntSetting):
                if not value or not value.isdigit():
                    raise TypeError('Must be a numerical value.')

                self.setting.value = int(value)

            elif isinstance(self.setting, StrSetting):
                self.setting.value = value

        except (ValueError, TypeError) as error:
            return self.failure(str(error))

        return self.success()


class SettingsScreen(ModalScreen):
    BINDINGS = [
        ('escape', 'dismiss', 'Dismiss'),
        ('g', 'show_tab("settings-screen-global-pane")', 'Global'),
        ('p', 'show_tab("settings-screen-platforms-pane")', 'Platforms'),
        ('l', 'show_tab("settings-screen-log-pane")', 'Log'),
        ('r', 'refresh_log', 'Refresh'),
    ]

    def __init__(self, settings: AppSettings) -> None:
        super().__init__()
        self.app_settings = settings

    # COMPOSE

    def _compose_setting_blocks(self, settings: dict[str, Setting], block_name: str) -> ComposeResult:
        for setting_name, setting in settings.items():
            if not setting.show:
                continue

            caption = Text(setting_name.replace('_', ' ').capitalize())

            with Vertical(classes='box'):
                if setting.description:
                    description = Text(f' ({setting.description}):', 'italic')
                    yield Label(caption + description, classes='settings-screen-labels')
                else:
                    yield Label(f'{caption}:', classes='settings-screen-labels')

                if isinstance(setting, IntSetting) or isinstance(setting, StrSetting):
                    if setting.fixed_values:
                        yield Select(
                            map(lambda x: (str(x), x), setting.fixed_values),
                            value=setting.value,
                            id=f'{block_name}-setting-{setting_name}',
                        )
                    else:
                        yield Input(
                            str(setting.value),
                            id=f'{block_name}-setting-{setting_name}',
                            validators=[SettingsValidator(setting)],
                            disabled=setting.read_only,
                            max_length=setting.max_length
                            if (isinstance(setting, StrSetting) and setting.max_length)
                            else 0,
                            type='integer' if isinstance(setting, IntSetting) else 'text',
                        )

                elif isinstance(setting, BoolSetting):
                    yield Switch(
                        setting.value,
                        id=f'{block_name}-setting-{setting_name}',
                        disabled=setting.read_only,
                    )

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical(id='settings-screen-left-block'):
                with TabbedContent():
                    with TabPane('Global settings', id='settings-screen-global-pane'):
                        yield from self.compose_global_pane()

                    with TabPane('Platform settings', id='settings-screen-platforms-pane'):
                        yield from self.compose_platforms_pane()

                    with TabPane('System log', id='settings-screen-log-pane'):
                        yield Lazy(Label('Use "r" to refresh the log below.'))
                        yield Rule()
                        yield Lazy(RichLog(id='settings-screen-system-log'))

            with Vertical(id='settings-screen-logo', classes='logo'):
                yield Label(LOGO.format(app_ver))

    def compose_platforms_pane(self) -> ComposeResult:
        with Lazy(VerticalScroll()):
            for name, platform in self.app_settings.platforms.items():
                with Collapsible(title=platform['full_name'].value):
                    yield from self._compose_setting_blocks(platform.settings, 'settings-screen-platform-' + name)

    def compose_global_pane(self) -> ComposeResult:
        with VerticalScroll():
            yield from self._compose_setting_blocks(self.app_settings.settings, 'settings-screen-global')

            yield Rule(line_style='heavy')

            text = Text('Play with the Theme setting above:')
            text.highlight_words(('Theme',), 'bold yellow')
            yield Label(text, classes='settings-screen-labels')

            yield (
                log := RichLog(
                    id='settings-screen-code-sample',
                    min_width=0,
                    highlight=True,
                    markup=True,
                    auto_scroll=False,
                )
            )
            log.write(
                Syntax(
                    CODE_SAMPLE,
                    'python',
                    theme=self.app_settings['theme'].value,
                    indent_guides=True,
                )
            )

    # ACTIONS

    def action_show_tab(self, tab: str) -> None:
        control = self.query_one(TabbedContent)
        control.active = tab

    def action_refresh_log(self) -> None:
        control = self.query_one('#settings-screen-system-log', RichLog)
        control.clear()

        highlighter = ReprHighlighter()

        for handler in self.app_settings.logger.handlers:
            if type(handler) is not BufferingHandler:
                continue

            for record in handler.buffer:
                try:
                    line = f'{record.asctime} {record.levelname} {record.message}'
                except Exception:
                    line = f'{record.levelname} {record.msg}'

                text = highlighter(line)

                if special_words := self.app_settings['logging_level'].fixed_values:
                    text.highlight_words(special_words, 'bold blue')

                control.write(text)

    # EVENTS

    @on(Input.Changed)
    def on_input_changed(self, event: Input.Changed) -> None:
        if not event.control.id:
            return

        if event.validation_result:
            if not event.validation_result.is_valid:
                self.notify(
                    ''.join(event.validation_result.failure_descriptions),
                    severity='error',
                    timeout=10,
                )
            else:
                self.app_settings.dump()

                for platform in self.app_settings.platforms.values():
                    platform.dump()

    @on(Select.Changed)
    def on_select_changed(self, event: Select.Changed) -> None:
        if not event.control.id:
            return

        if event.control.id.startswith('settings-screen-global'):
            setting_name = event.control.id.replace('settings-screen-global-setting-', '')
            setting = self.app_settings[setting_name]

            if isinstance(setting, IntSetting):
                setting.value = int(str(event.control.value))

            elif isinstance(setting, StrSetting):
                setting.value = str(event.control.value)

            if setting_name == 'theme':
                code_sample = self.query_one('#settings-screen-code-sample', RichLog)
                code_sample.clear()
                code_sample.write(
                    Syntax(
                        CODE_SAMPLE,
                        'python',
                        theme=setting.value,
                        indent_guides=True,
                    ),
                )

            self.app_settings.dump()

        elif event.control.id.startswith('settings-screen-platform'):
            parts = event.control.id.split('-')
            platform_name = parts[3]
            setting_name = '-'.join(parts[5:])

            platform = self.app_settings.platforms[platform_name]

            if isinstance(platform[setting_name], IntSetting):
                platform[setting_name].value = int(str(event.control.value))

            elif isinstance(platform[setting_name], StrSetting):
                platform[setting_name].value = str(event.control.value)

            platform.dump()

    @on(Switch.Changed)
    def on_switch_changed(self, event: Switch.Changed) -> None:
        if not event.control.id:
            return

        if event.control.id.startswith('settings-screen-global'):
            setting_name = event.control.id.replace('settings-screen-global-setting-', '')
            setting = self.app_settings[setting_name]

            if isinstance(setting, BoolSetting):
                setting.value = event.control.value

            if setting_name == 'night_mode':
                self.app.dark = setting.value

            self.app_settings.dump()

        elif event.control.id.startswith('settings-screen-platform'):
            parts = event.control.id.split('-')
            platform_name = parts[3]
            setting_name = '-'.join(parts[5:])

            platform = self.app_settings.platforms[platform_name]

            if isinstance(platform[setting_name], BoolSetting):
                platform[setting_name].value = event.control.value

            platform.dump()

    @on(TabbedContent.TabActivated)
    def on_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        assert event.tab.id
        if 'log' in event.tab.id:
            self.action_refresh_log()
