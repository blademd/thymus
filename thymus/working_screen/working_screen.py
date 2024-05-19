from __future__ import annotations

import os

from pathlib import Path

from typing import cast, Literal, Optional
from collections.abc import Iterator
from dataclasses import dataclass

from textual import on, work
from textual.app import ComposeResult
from textual.screen import Screen
from textual.worker import Worker, get_current_worker
from textual.reactive import var
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.css.query import NoMatches

from rich.text import Text
from rich.syntax import Syntax

from thymus.settings import AppSettings
from thymus.contexts import Context
from thymus.responses import Response
from thymus.modals import OpenScreenResult, OpenScreenNetworkData, ErrorScreen
from thymus.working_screen.path_bar import PathBar
from thymus.working_screen.editor import Editor, StopRollingBack, PreCommitCheckFailed
from thymus.working_screen.command_line import CommandLine
from thymus.working_screen.viewer import Viewer
from thymus.working_screen.sidebar import Sidebar
from thymus.working_screen.editor_overlay import EditorOverlay
from thymus.working_screen.screen_footer import ScreenFooter
from thymus.working_screen.help import help


class WorkingScreen(Screen):
    BINDINGS = [
        ('escape', 'request_quit', 'Quit'),
        ('ctrl+b', 'toggle_sidebar', 'Toggle sidebar'),
    ]

    mode: var[Literal['view', 'edit']] = var('view')
    path = var('')
    virtual_path = var('')
    platform_name = var('')
    encoding = var('')
    source: var[Literal['local', 'remote']] = var('local')
    delimiter = var('')
    current_context = var(0)
    spaces = var(0)
    theme = var('')
    context_name = var('')

    @dataclass
    class FetchDone(Message):
        content: list[str]

    @dataclass
    class FetchFailed(Message):
        uid: str
        reason: str

    @dataclass
    class NewBatch(Message):
        batch: tuple[str, int]
        status: Literal['error', 'success']
        mode: Literal['data', 'rich', 'system']

    @dataclass
    class Release(Message):
        screen: WorkingScreen
        error: str

    @property
    def shortcut(self) -> Context:
        assert len(self.contexts) and len(self.contexts) > self.current_context and self.contexts[self.current_context]
        return self.contexts[self.current_context]

    def __init__(self, name: str, data: OpenScreenResult, settings: AppSettings) -> None:
        super().__init__(name=name)
        self.settings = settings
        self.drawing_thread: Optional[Worker] = None
        self.content: list[str] = []  # content is always a list of lines with the a new line escape for each line
        self.contexts: list[Context] = []
        self.platform = data.platform
        self.platform_name = data.platform['short_name'].value
        self.encoding = data.encoding
        self.source = data.source
        self.editor_feed_size = 0
        self.theme = settings['theme'].value
        self.loading = True
        self.fetch_content(data.target, device_type=data.platform['device_type'].value)

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical(id='working-screen-left-siderbar'):
                yield (sidebar := Sidebar(limit=self.settings['sidebar_max_length'].value))

            with Vertical():
                with Vertical():
                    yield Viewer()
                    yield Editor(
                        frequency=self.settings['editor_frequency_factor'].value, classes='disabled'
                    ).data_bind(WorkingScreen.virtual_path)

                with Vertical(id='working-screen-right-bottom-block'):
                    yield PathBar(id='working-screen-path').data_bind(
                        WorkingScreen.mode, WorkingScreen.virtual_path, WorkingScreen.delimiter
                    )
                    yield CommandLine(
                        placeholder='>', id='working-screen-inputs-main', autocomplete_cb=sidebar.get_replacement
                    )

        yield EditorOverlay()
        yield ScreenFooter(id='working-screen-footer').data_bind(
            WorkingScreen.mode,
            WorkingScreen.path,
            WorkingScreen.platform_name,
            WorkingScreen.encoding,
            WorkingScreen.source,
            WorkingScreen.current_context,
            WorkingScreen.spaces,
            WorkingScreen.theme,
            WorkingScreen.context_name,
        )

    # EVENTS

    def on_show(self) -> None:
        self.query_one(CommandLine).focus()

    def on_release(self) -> None:
        for context in self.contexts:
            context.release()

    @on(FetchDone)
    def on_fetch_done(self, event: FetchDone) -> None:
        self.content = event.content

        if self.source == 'local':
            if (editor := self.query_one(Editor)).load(self.path) and (context_id := editor.last_context_id):
                self.build_primary_context(context_id=context_id)
                self.current_context = context_id

                for cid in range(context_id - 1, -1, -1):
                    context = self.contexts[-1]
                    self.request_rollback(cid, cleanup=False, context=context)  # modifies self.content
                    self.build_primary_context(context_id=cid)  # builds a new context & puts it at the end

                self.contexts.reverse()
                self.content = open(self.path, encoding=self.encoding, errors='ignore').readlines()
                self.set_active_context(self.contexts[context_id])

                for context in self.contexts:
                    context._content = self.content

                editor.restore_history()
            else:
                self.build_primary_context()
                self.set_active_context(self.shortcut)
        else:
            self.build_primary_context()
            self.set_active_context(self.shortcut)

        message = f'Source "{self.path}" successfully opened.'
        self.settings.logger.info(message)

    @on(NewBatch)
    def on_new_batch(self, event: NewBatch) -> None:
        viewer = self.query_one(Viewer)
        if event.mode == 'data':
            theme = self.settings['theme'].value
            width = viewer.size.width - 2
            text, code_width = event.batch
            text = text.rstrip()
            code_width = max(width, code_width)
            lexer = self.shortcut.lexer()
            syntax = Syntax(code=text, theme=theme, lexer=lexer, code_width=code_width)
            viewer.write(syntax, scroll_end=False)
        elif event.mode == 'rich':
            viewer.markup = True
            viewer.write(event.batch[0], scroll_end=False)
            viewer.markup = False
        else:
            color = 'green' if event.status == 'success' else 'red'
            viewer.write(Text(event.batch[0], style=color), scroll_end=False)

    @on(CommandLine.NewCommand)
    def on_new_command(self, event: CommandLine.NewCommand) -> None:
        self.process_command(event.command)

    @on(CommandLine.LineChanged)
    def on_command_line_changed(self, event: CommandLine.LineChanged) -> None:
        if self.mode != 'view':
            return

        sidebar = self.query_one(Sidebar)

        if event.current_value:
            if '| ' in event.current_value:
                return

            sidebar.update(self.shortcut.get_possible_sections(event.current_value))
        else:
            sidebar.clear()

    @on(EditorOverlay.Stop)
    def on_loading_stop(self, _) -> None:
        import time

        time.sleep(self.settings['editor_frequency_factor'].value / 10)

        self.query_one(EditorOverlay).message = ''
        self.query_one(Editor).exit_edit()
        self.mode = 'view'

    @on(Editor.LoadComplete)
    def on_editor_load_complete(self, _) -> None:
        self.query_one(EditorOverlay).message = ''

    def on_quit_cb(self, result: bool) -> None:
        if result:
            self.post_message(WorkingScreen.Release(self, ''))

    def on_lines_count_change_cb(self, value: int) -> None:
        if value:
            self.query_one(EditorOverlay).message = f'loading • {value}/{self.editor_feed_size}'

    # WATCHERS

    def watch_mode(self) -> None:
        try:
            viewer = self.query_one(Viewer)
            editor = self.query_one(Editor)
            sidebar = self.query_one(Sidebar)

            if self.mode == 'edit':
                if self.drawing_thread:
                    self.drawing_thread.cancel()

                viewer.exit_view()
                sidebar.exit_view()

                begin, end = self.shortcut.path_offset
                data = self.content[begin:end]

                editor.enter_edit(data, self.size.height * self.settings['editor_scale_factor'].value)
                self.editor_feed_size = len(data)
                self.watch(editor, 'lines_count', self.on_lines_count_change_cb)
            elif self.mode == 'view':
                editor.exit_edit()
                viewer.enter_view()
                sidebar.enter_view()
        except NoMatches:
            ...

    # ACTIONS

    def action_request_quit(self) -> None:
        from thymus.modals import QuitScreen

        self.app.push_screen(QuitScreen(), self.on_quit_cb)

    def action_toggle_sidebar(self) -> None:
        sidebar = self.query_one('#working-screen-left-siderbar')

        if sidebar.styles.display == 'block':
            sidebar.styles.display = 'none'
        else:
            sidebar.styles.display = 'block'

    # ADDITIONAL ROUTINES

    def configure_context(self, context: Context, *, exit_on_error=True) -> bool:
        for k, v in self.platform.settings.items():
            if not v.pass_through:
                continue

            try:
                setattr(context, k, v.value)
            except Exception as error:
                err_msg = f'Cannot configure the settings "{k}" for a platform {self.platform_name.upper()}. '
                err_msg += f'Value: "{v.value}". Exception: {error}'
                self.settings.logger.error(str(error))

        try:
            context.build()
        except Exception as error:
            if exit_on_error:
                self.app.switch_screen(ErrorScreen(str(error)))
                self.post_message(WorkingScreen.Release(self, str(error)))
            else:
                self.notify(str(error), severity='error')

            return False

        return True

    def set_active_context(self, context: Context) -> None:
        if not context.is_built:
            return

        context.on_enter(f'{self.shortcut.alias_command_top}')  # in case of rollbacks
        self.virtual_path = context.path
        self.delimiter = context.delimiter
        self.query_one(Sidebar).get_virtual_cb = context.get_virtual_from
        self.query_one(Sidebar).update(context.get_possible_sections(f'{context.alias_command_go} |'))
        self.process_view_help_command(context)
        self.spaces = context.spaces
        self.context_name = context.name

    def build_primary_context(self, *, context_id=0) -> None:
        context = self.platform.link_context(  # type: ignore
            context_id=context_id,
            name='',
            content=self.content,
            encoding=self.encoding,
            neighbors=self.contexts,
            saves_dir=self.settings.where_to_save(),
        )
        self.configure_context(context)
        self.contexts.append(context)
        self.loading = False

    def add_context(self, commit: str) -> bool:
        begin, end = self.shortcut.path_offset

        if len(self.content) < end:
            self.notify('Commit failed. Length mismatch.')
            return False

        commit_data = commit.splitlines(keepends=True)

        try:
            self.shortcut.validate_commit(commit_data)
        except ValueError as error:
            self.notify(str(error), severity='error')
            return False

        # We need no more this part of the content
        del self.content[begin:end]

        # Replace it with the data from the commit
        for line in commit_data:
            self.content.insert(begin, line)
            begin += 1

        # Create a new instance of the context
        next_context = self.platform.link_context(  # type: ignore
            context_id=self.current_context + 1,
            name='' if not self.shortcut.name else f'{self.shortcut.name}_commit_{self.current_context + 1}',
            content=self.content,
            encoding=self.encoding,
            neighbors=self.contexts,
            saves_dir=self.settings.where_to_save(),
        )

        # Try to configure & build it
        if not self.configure_context(next_context, exit_on_error=False):
            return False

        self.contexts.append(next_context)
        self.current_context += 1

        # Move path to the root
        self.virtual_path = next_context.path

        # After a commit we need to set the auto-completion callback to the next_context
        self.query_one(Sidebar).get_virtual_cb = next_context.get_virtual_from

        return True

    def process_view_context_command(self, value: str) -> None:
        try:
            if self.drawing_thread:
                self.drawing_thread.cancel()

            response = self.shortcut.on_enter(value)

            if response.status == 'success':
                if response.value:
                    if response.mode != 'system':
                        self.query_one(Viewer).clear()
                        self.drawing_thread = self.draw(response)
                    else:
                        self.notify(' '.join(response.value))

                self.virtual_path = self.shortcut.path
                self.spaces = self.shortcut.spaces
                self.context_name = self.shortcut.name
            else:
                err_msg = ' '.join(response.value)
                self.notify(err_msg, severity='error')
        except Exception as err:
            self.notify(str(err), severity='error')

    def process_view_save_command(self) -> None:
        if self.source == 'remote':
            self.notify('Remote source is not supported.', severity='error')
            return

        try:
            self.query_one(Editor).save(self.path)

            with open(self.path, 'w', encoding='utf-8') as f:
                f.writelines(self.content)
                f.flush()
                os.fsync(f.fileno())
        except Exception as error:
            self.notify('Save failed, see the system log.', severity='error')
            self.settings.logger.error(f'Error has occurred: {error}. Save failed.')
            return

        self.notify('History saved.')

    def process_view_help_command(self, context: Context) -> None:
        self.query_one(Viewer).clear()

        if self.drawing_thread:
            self.drawing_thread.cancel()

        templates_folder = Path(self.settings['templates_folder'].value)
        help_filename = Path(self.settings['context_help'].value)

        path = Path(__file__).resolve().parent.parent / templates_folder / help_filename

        if (help_info := help(str(path), self.platform_name, context)).value:
            self.drawing_thread = self.draw(help_info)

    def process_edit_commit_command(self) -> None:
        editor = self.query_one(Editor)

        if editor.loading:
            self.notify('Editor is loading...', severity='error')
            return

        try:
            commit_data = editor.commit()

            if not self.add_context(commit_data):
                editor.purge_last_commit()

            if self.settings['save_on_commit'].value:
                self.process_view_save_command()

            self.mode = 'view'
        except PreCommitCheckFailed as error:
            self.notify(str(error), severity='error')

    def process_edit_rollback_command(self, value: str) -> None:
        if self.query_one(Editor).loading:
            self.notify('Editor is loading...', severity='error')
            return

        id_part = value.replace('rollback ', '')
        id_part = id_part.strip()

        if not id_part.isdigit():
            self.notify('Rollback ID must be a digit.', severity='error')
            return

        self.request_rollback(int(id_part))
        self.set_active_context(self.shortcut)

    def process_command(self, value: str) -> None:
        if self.mode == 'view':
            if value == 'edit':
                self.mode = 'edit'
            elif value == 'save':
                self.process_view_save_command()
            elif value == 'help':
                self.process_view_help_command(self.shortcut)
            else:
                self.process_view_context_command(value)
        else:
            if value == 'commit':
                self.process_edit_commit_command()
            elif value == 'view' or value == 'exit':
                self.mode = 'view'
            else:
                if value.startswith('rollback '):
                    self.process_edit_rollback_command(value)
                else:
                    self.notify('Unknown command.', severity='error')

    def request_rollback(self, rollback_id: int, *, cleanup=True, context: Optional[Context] = None) -> None:
        if rollback_id < 0 or not self.current_context:
            return

        control = self.query_one(Editor)
        control.loading = True

        iterations = control.rollback_count_to(rollback_id)

        try:
            for _ in range(iterations):
                shortcut = context if context else self.shortcut
                rollback_iter = control.rollback(cleanup)
                virtual_path = next(rollback_iter)
                begin, end, rollback_config = shortcut.get_rollback_config(virtual_path)
                rollback_iter.send(rollback_config)

                del self.content[begin:end]

                if cleanup:
                    context_to_release = self.contexts.pop(self.current_context)
                    context_to_release.release()
                    self.current_context -= 1

                for line in rollback_iter:
                    self.content.insert(begin, line)
                    begin += 1
        except ValueError as error:
            self.settings.logger.error(str(error))
            self.notify(str(error), severity='error')
        except StopIteration:
            self.settings.logger.error('Unknown error during the rolling back #1.')
            self.notify('Rollback failed.', severity='error')
        except StopRollingBack:
            self.settings.logger.error('Unknown error during the rolling back #2.')
            self.notify('Rollback failed.', severity='error')
        finally:
            control.loading = False
            self.mode = 'view'

    @work(exclusive=True, exit_on_error=False)
    async def fetch_content(self, target: str | OpenScreenNetworkData, *, device_type='') -> None:
        assert self.name

        if self.source == 'local':
            target = cast(str, target)
            self.path = target

            try:
                if content := open(target, encoding=self.encoding, errors='ignore').readlines():
                    self.post_message(WorkingScreen.FetchDone(content))
                else:
                    self.post_message(WorkingScreen.FetchFailed(self.name, f'File "{target}" is empty.'))
            except FileNotFoundError:
                self.post_message(WorkingScreen.FetchFailed(self.name, f'File "{target}" does not exist.'))
            except OSError:
                self.post_message(WorkingScreen.FetchFailed(self.name, f'File "{target}" is incorrect.'))
            except Exception as error:
                self.post_message(WorkingScreen.FetchFailed(self.name, f'Unknown error at local open: {error}'))
        else:
            from thymus.netloader import create, TimeoutError, DisconnectError, KeyError

            target = cast(OpenScreenNetworkData, target)
            self.path = f'{target.host}:{target.port}'

            try:
                connection_data = {
                    'device_type': device_type,
                    'host': target.host,
                    'port': target.port,
                    'username': target.username,
                    'protocol': target.protocol,
                    'timeout': self.settings['network_connection_timeout'].value,
                }

                if target.passphrase:
                    connection_data['passphrase'] = target.passphrase
                else:
                    connection_data['password'] = target.password

                if target.secret:
                    connection_data['secret'] = target.secret

                async with create(**connection_data, logger=self.settings.logger) as connect:
                    output = await connect.fetch_config()

                    if output:
                        self.post_message(WorkingScreen.FetchDone(output.splitlines(keepends=True)))
                    else:
                        self.post_message(WorkingScreen.FetchFailed(self.name, 'Remote response was empty.'))
            except (KeyError, TimeoutError, DisconnectError) as error:
                self.post_message(WorkingScreen.FetchFailed(self.name, str(error)))
            except Exception as error:
                self.post_message(WorkingScreen.FetchFailed(self.name, f'Unknown error at remote open: {error}'))

    @work(thread=True)
    def draw(self, data: Response) -> None:
        import time

        def batch_producer(limit: int) -> Iterator[tuple[str, int]]:
            batch = ''
            counter = 0
            max_width = 0

            for line in data.value:
                batch += line + '\n'
                counter += 1
                max_width = max(len(line), max_width)

                if counter % limit == 0:
                    yield batch, max_width
                    batch = ''
                    counter = 0
            yield batch, max_width

        worker = get_current_worker()

        for batch in batch_producer(limit=self.size.height):
            if worker.is_cancelled:
                break
            self.post_message(WorkingScreen.NewBatch(batch, data.status, data.mode))
            time.sleep(0.2)
