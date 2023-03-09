from __future__ import annotations

from typing import cast
from random import random

from textual.strip import Strip
from textual.geometry import Size
from textual.widgets import TextLog
from rich.console import RenderableType
from rich.text import Text
from rich.measure import measure_renderables
from rich.pretty import Pretty
from rich.protocol import is_renderable
from rich.segment import Segment


class ExtendedTextLog(TextLog):
    def write(
        self,
        content: RenderableType | object,
        width: int | None = None,
        expand: bool = False,
        shrink: bool = True,
    ) -> None:
        """Write text or a rich renderable.

        Args:
            content: Rich renderable (or text).
            width: Width to render or None to use optimal width. Defaults to `None`.
            expand: Enable expand to widget width, or False to use `width`. Defaults to `False`.
            shrink: Enable shrinking of content to fit width. Defaults to `True`.
        """

        renderable: RenderableType
        if not is_renderable(content):
            renderable = Pretty(content)
        else:
            if isinstance(content, str):
                if self.markup:
                    renderable = Text.from_markup(content)
                else:
                    renderable = Text(content)
                if self.highlight:
                    renderable = self.highlighter(renderable)
            else:
                renderable = cast(RenderableType, content)

        console = self.app.console
        render_options = console.options

        if isinstance(renderable, Text) and not self.wrap:
            render_options = render_options.update(overflow="ignore", no_wrap=True)

        render_width = measure_renderables(
            console, render_options, [renderable]
        ).maximum
        container_width = (
            self.scrollable_content_region.width if width is None else width
        )
        if container_width:
            if expand and render_width < container_width:
                render_width = container_width
            if shrink and render_width > container_width:
                render_width = container_width

        segments = self.app.console.render(
            renderable, render_options.update_width(render_width)
        )
        lines = list(Segment.split_lines(segments))
        if not lines:
            return

        self.max_width = max(
            self.max_width,
            max(sum(segment.cell_length for segment in _line) for _line in lines),
        )
        strips = Strip.from_lines(lines)
        for strip in strips:
            strip.adjust_cell_length(render_width)
        self.lines.extend(strips)

        if self.max_lines is not None and len(self.lines) > self.max_lines:
            self._start_line += len(self.lines) - self.max_lines
            self.refresh()
            self.lines = self.lines[-self.max_lines:]
        self.virtual_size = Size(self.max_width, len(self.lines))
        # here is no the scroll_end() call

    def on_mouse_scroll_down(self) -> None:
        if random() <= 0.25:
            self.screen.draw()
