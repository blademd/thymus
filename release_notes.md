# Version 0.1.1-alpha

* Textual support updated to the latest version (v0.24.1).
* The open dialog was redesigned.
* An extended textlog widged's code was simplified with the scroll_end option.

# Version 0.1.2-alpha

* The main menu was redesigned.
* Thymus supports settings and the settings file now.
* User can manipulate the settings via the `global` commands.
* Syntax highlighting.
* The `up show` modificator for the TUI part.
* Fixed bug with double rows of the TreeView in the open dialog.
* Fixed bug with the Input in the open dialog, it supports Enter hit now.
* Fixed bug with ths save modificator, it does not crash the app now.

# Version 0.1.3-alpha

## New

* Cisco IOS (IOS-XE), Arista EOS support.
* Now you can close a working context with the Escape key (with a confirmation dialog).
* Logging system with rotating files. Log files are stored in the "logs/" folder. The config file for the logging is "settings/logging.conf".
** Logs are accessible inside the Application via a modal dialog (Ctrl+L).

# Changes

* Textual version 0.29.0.
* Main screen was redesigned. It does not contain any active elements anymore.
* Dark mode is now a night mode (Ctrl+N). Ctrl+D is no longer available.

## Enhancements

* CLIer supports all the same platforms as TUIer does.
* Auto-completion is now case-insensitive.
* A pipe (`|`) symbol at the end of a line fills out the left sidebar of a working screen with all possible options.
* Exit is through a confirmation dialog. You can't accidentally close the app now.
* Switching among contexts is on a separate screen now (Ctrl+S).
* Elements for auto-complete on a left sidebar are artificially limited. The limit is configurable via the `global set sidebar_limit N` and the "settings/thymus.json" file.
* All platforms can be tuned via `global set platform ...` commands and in the "settings/thymus.json" file.
* Tab key does not move the focus from an Input filed in a working context.
* Auto-completion is improved and faster.
* Path bar in a working screen adapts to screen width changes.
* Statusbar in a working screen adapts to screen width changes.
* Statusbar was redesigned, it shows a platform type now, and some elements were moved.
* A horizontal scroll bar of a text field in a working screen adapts to the longest line.
* Lots of refactoring.

## Fixes

* Several JunOS lexer's bugs.
* The `top show` command works as expected now.
* The open dialog is now modal, you can't create more than one at the same time.
* In a working screen the text field's background color now adapts to day/night mode. However, it requires some scrolling down sometimes...
* All exceptions for a context are handled and logged/printed to a screen, instead of crashing the app.
* Left sidebar in a working screen now preserves a section's name after the pressing of the Space key.
* Now you can't name two or more contexts for the same platform with the same name.
* If the content of two different files was the same `compare`, and `diff` calls crashed the app.
* An empty input field of a working screen crashed the app after pressing the Enter key.
* Minor bugs.
