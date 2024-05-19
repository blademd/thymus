from __future__ import annotations

import json

from thymus.responses import Response
from thymus.contexts import Context


def help(template_path: str, platform_name: str, context: Context) -> Response:
    try:
        f = open(template_path, encoding='utf-8')
        data: dict = json.load(f)

        if not data:
            return Response.success()

        body: list[str] = []

        body.append(data['header'].format(NOS=platform_name))

        for k, v in data['singletones'].items():
            if k == 'show':
                body.append(v.format(CMD=context.alias_command_show))
            elif k == 'go':
                body.append(v.format(CMD=context.alias_command_go))
            elif k == 'top':
                body.append(v.format(CMD=context.alias_command_top))
            elif k == 'up':
                body.append(v.format(CMD=context.alias_command_up))
            elif k == 'set' or k == 'help':
                body.append(v)

        body.append(data['modificators_header'])

        for k, v in data['modificators'].items():
            if k == 'filter':
                body.append(v.format(CMD=context.alias_sub_command_filter))
            elif k == 'wildcard':
                body.append(v.format(CMD=context.alias_sub_command_wildcard))
            elif k == 'stubs':
                body.append(v.format(CMD=context.alias_sub_command_stubs))
            elif k == 'sections':
                body.append(v.format(CMD=context.alias_sub_command_sections))
            elif k == 'save':
                body.append(v.format(CMD=context.alias_sub_command_save))
            elif k == 'count':
                body.append(v.format(CMD=context.alias_sub_command_count))
            elif k == 'diff':
                body.append(v.format(CMD=context.alias_sub_command_diff))
            elif k == 'contains':
                body.append(v.format(CMD=context.alias_sub_command_contains))
            elif k == 'reveal':
                body.append(v)

        result = Response.success(body)
        result.mode = 'rich'

        return result

    except Exception:
        return Response.success()
