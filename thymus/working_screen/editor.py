from __future__ import annotations

import re
import os
import msgpack  # type: ignore

from dataclasses import dataclass
from typing import Optional, cast
from collections.abc import Generator, Iterable, Iterator

from textual import on, work
from textual.widgets import TextArea
from textual.document._edit import Edit
from textual.document._document import EditResult
from textual.reactive import var, reactive
from textual.worker import Worker, get_current_worker
from textual.message import Message

from thymus.utils import get_spaces


class StopRollingBack(Exception): ...


class PreCommitCheckFailed(Exception): ...


class Editor(TextArea):
    @dataclass
    class NewBatch(Message):
        batch: tuple[str, int, Optional[int]]

    @dataclass
    class LoadComplete(Message):
        size: int

    virtual_path = var('')
    lines_count = reactive(0)

    @property
    def last_context_id(self) -> int:
        return len(self.commit_history) - 1

    def __init__(self, frequency: int, *args, **kwargs) -> None:
        self._shadow_history: dict[int, tuple[str, list[Edit]]] = {}
        self._shadow_history[0] = ('', [])
        self.commit_history: dict[int, tuple[str, list[Edit]]] = {}
        self.commit_history[0] = ('', [])  # default commit, must always exist
        self.change_log: list[Edit] = []
        self.drawing_thread: Optional[Worker] = None
        self.frequency = frequency / 10
        self.min_indent: Optional[int] = None

        super().__init__(soft_wrap=False, tab_behavior='indent', *args, **kwargs)

    def edit(self, edit: Edit) -> EditResult:
        self.change_log.append(edit)
        return super().edit(edit)

    def undo(self) -> None:
        if edits := self.history._pop_undo():
            for edit in edits:
                self.change_log.remove(edit)
            self._undo_batch(edits)

    def redo(self) -> None:
        if edits := self.history._pop_redo():
            self.change_log.extend(edits)
            self._redo_batch(edits)

    def enter_edit(self, data: list[str], current_height: int) -> None:
        self.text = ''
        self.styles.display = 'block'
        self.lines_count = 0

        if self.drawing_thread:
            self.drawing_thread.cancel()

        self.change_log = []
        self.loading = True
        self.drawing_thread = self.draw(data, current_height)

    def exit_edit(self) -> None:
        if self.drawing_thread:
            self.drawing_thread.cancel()
            self.lines_count = 0

        self.styles.display = 'none'
        self.change_log = []
        self.min_indent = None
        self.text = ''

    def commit(self) -> str:
        if not self.change_log:
            raise PreCommitCheckFailed('Nothing to commit.')

        if not self.text:
            raise PreCommitCheckFailed('Empty commit is prohibited.')

        if not self.text.endswith('\n'):
            raise PreCommitCheckFailed('Text must end with a new line symbol.')

        lines = self.text.splitlines()

        for line in lines:
            if line.strip():
                break
        else:
            raise PreCommitCheckFailed('Empty commit is prohibited.')

        if self.min_indent is not None:
            for line in lines:
                if get_spaces(line) < self.min_indent:
                    raise PreCommitCheckFailed('Indentation error.')

        commit_id = len(self.commit_history)
        self.commit_history[commit_id] = (self.virtual_path, self.compress_commit(self.change_log))
        self.change_log = []

        return self.text

    def compress_commit(self, edits: list[Edit]) -> list[Edit]:
        result: list[Edit] = []
        last_line = 0
        last_col = 0

        for edit in edits:
            if not result:
                result.append(edit)
                last_line, last_col = edit.to_location
                continue

            line, col = edit.from_location

            if last_line == line and last_col == col - 1 and edit.text != '\n':
                last_edit = result[-1]
                last_edit.text += edit.text
                last_edit.to_location = edit.to_location
                last_edit._edit_result = EditResult(
                    end_location=(last_edit.to_location[0], last_edit.to_location[1] + 1), replaced_text=''
                )
            else:
                result.append(edit)

            last_line, last_col = edit.to_location

        return result

    def purge_last_commit(self) -> None:
        if self.commit_history:
            key = len(self.commit_history) - 1
            del self.commit_history[key]

    def rollback_count_to(self, target_id: int) -> int:
        if target_id >= len(self.commit_history):
            return 0

        return len(self.commit_history) - target_id - 1

    def rollback(self, cleanup=True) -> Generator[str, Iterable[str], None]:
        end = len(self.commit_history) - 1

        if end <= 0:
            return

        virtual_path, data = self.commit_history[end]

        text = yield virtual_path
        yield ''  # to feed the send call with no data

        if not text:
            raise StopRollingBack

        self.load_text(''.join(text))

        self._undo_batch(data)

        if not cleanup:
            self._shadow_history[end] = self.commit_history[end]

        del self.commit_history[end]

        for match_line in re.finditer(r'(?:[^\n]+)?\n', self.text):
            yield match_line.group()

    def save(self, target: str) -> None:
        if self.change_log:
            return

        storage: dict = {}
        target = target + '.history'

        for index, edit_pair in self.commit_history.items():
            virtual_path, edits = edit_pair

            storage[str(index)] = {}
            storage[str(index)][virtual_path] = []

            for edit in edits:
                assert edit._edit_result

                container = {
                    'x': edit.text,
                    'f': edit.from_location,
                    't': edit.to_location,
                    'm': edit.maintain_selection_offset,
                    'e': edit._edit_result.end_location,
                    'r': edit._edit_result.replaced_text,
                }
                storage[str(index)][virtual_path].append(container)

        with open(target, 'bw') as f:
            f.write(msgpack.packb(storage))
            f.flush()
            os.fsync(f.fileno())

    def load(self, target: str) -> bool:
        target = target + '.history'

        try:
            with open(target, 'br') as f:
                bytes_data = f.read()
                history_data = msgpack.unpackb(bytes_data)
        except Exception:
            return False

        for index, data in history_data.items():
            data = cast(dict, data)

            try:
                index = int(index)
            except ValueError:
                return False

            if index == 0:
                continue

            for virtual_path, edits in data.items():
                virtual_path = cast(str, virtual_path)
                edits = cast('list[Edit]', edits)

                store: list[Edit] = []

                for edit_data in edits:
                    try:
                        f_tuple = (int(edit_data['f'][0]), int(edit_data['f'][1]))
                        t_tuple = (int(edit_data['t'][0]), int(edit_data['t'][1]))
                        e_tuple = (int(edit_data['e'][0]), int(edit_data['e'][1]))

                        edit = Edit(
                            text=edit_data['x'],
                            from_location=f_tuple,
                            to_location=t_tuple,
                            maintain_selection_offset=edit_data['m'],
                        )
                        edit._edit_result = EditResult(e_tuple, edit_data['r'])

                        store.append(edit)
                    except (ValueError, IndexError, KeyError):
                        break

                self.commit_history[index] = (virtual_path, store)

        if self.last_context_id == 0:
            return False

        return True

    def restore_history(self) -> None:
        self.commit_history = self._shadow_history

    @on(NewBatch)
    def on_new_batch(self, event: Editor.NewBatch) -> None:
        text, counter, min_indent = event.batch
        self.text += text
        self.lines_count += counter
        self.min_indent = min_indent

    @work(thread=True)
    def draw(self, data: list[str], limit: int) -> None:
        import time

        def batch_producer() -> Iterator[tuple[str, int, Optional[int]]]:
            batch = ''
            counter = 0
            min_indent = None

            for line in data:
                batch += line
                counter += 1

                if min_indent is None:
                    min_indent = get_spaces(line)
                else:
                    min_indent = min(min_indent, get_spaces(line))

                if counter % limit == 0:
                    yield batch, counter, min_indent
                    batch = ''
                    counter = 0
            yield batch, counter, min_indent

        worker = get_current_worker()
        for batch in batch_producer():
            if worker.is_cancelled:
                break
            self.post_message(Editor.NewBatch(batch))
            time.sleep(self.frequency)

        self.post_message(Editor.LoadComplete(self.lines_count))
        self.loading = False
