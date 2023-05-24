# Thymus

[Thymus](https://en.wikipedia.org/wiki/Thymus_(plant)) — is a tool for convenient navigation through network devices' config files. The tool does not require a connection to any network device (but it can be used over SSH from a remote machine). You just need to save a configuration file, open it anytime via the tool, and navigate through the config as easily as via a device's CLI.

Currently, Thymus supports only the Juniper Junos OS tree-view configuration (*the set-mode is not supported!*).

*This is the early alpha version! So some glitches can be appearing.*

## Requirements

Tested with Python **3.8.10**.

Thymus uses [Textual](https://github.com/Textualize/textual) as its TUI part so all the requirements of the latter are applicable to the former. There are no additional requirements (except your courage for sure).

## Modes

Thymus operates in two modes:

- **TUI-based**. This mode draws the full-scale user interface in your console with mouse support. From the Textual documentation:

	> On modern terminal software (installed by default on most systems), Textual apps can use **16.7 million** colors with mouse support and smooth flicker-free animation. A powerful layout engine and re-usable components makes it possible to build apps that rival the desktop and web experience.

	> Textual runs on Linux, macOS, Windows and probably any OS where Python also runs.

- **CLI-based**. This is a hardcore mode for old men who yell at clouds. At least, it works for old terminals without mouse support.

To run the TUI-mode use the command:
```
python -m thymus
```
```
python -m thymus tuier
```
The CLI-mode is invoked by:
```
python -m thymus clier
```

## Keyboard shortcuts (only for TUI)

- `Ctrl+D` to toggle the dark mode. Yes, it supports dark mode. All current stuff supports it why doesn't Thymus have to?
- `Ctrl+O` to open a file from any place of the tool.
- `Esc` to escape from the open file dialog.
- `Ctrl+B` to toggle the sidebar of the working screen.
- `Ctrl+S` to switch from the current screen to the default one.
- `Tab` to autocomplete a symbol or symbols inside the input box of the working screen.
- `Arrow Up/Down` to navigate over sections of the sidebar.
- `Ctrl+C` to immediately exit the application (**warning**, it does not ask you for mercy!)

## Selecting and copying the text

From the Textual documentation:

	Running a Textual app puts your terminal in to application mode which disables clicking and dragging to select text.
	Most terminal emulators offer a modifier key which you can hold while you click and drag to restore the behavior you
	may expect from the command line. The exact modifier key depends on the terminal and platform you are running on.

	- iTerm: Hold the OPTION key.
	- Gnome Terminal: Hold the SHIFT key.
	- Windows Terminal: Hold the SHIFT key.

	Refer to the documentation for your terminal emulator, if it is not listed above.

# Usage

## Context vs. global

When you open a config file you get access to the Working view. This view allows you to navigate through the config file, filter some output, save it, etc. Thymus supports two configurable instances: context and global. The context instance describes the settings of a configuration that is opened in the Working view. Currently, there is only the JunOS context available. The global instance allows you to manipulate settings of Thymus itself. Context's settings are manipulated via the `set` command, global -- the `global set` command.

The global settings are stored in the `thymus\settings\global.json` file. Thymus creates this directory and file at its startup if it is able to.

## Global commands list

- `global show themes` command lists all available highlighting themes.
- `global set theme` command allows you to choose any theme from the list.

## Context commands list

- `set` command allows you to configure some system-wide settings for the current context. It supports now:
- - `name` is to set the name of the context. This name is required by the `compare` modificator of the `show` command.
- - `spaces` is to set the indentation length for the `show` command.
- - `encoding` is to set the encoding for the `save` modificator.

## Junos commands list

The behavior of the tool mimics Junos CLI. Some commands are replaced with more handy analogs.

- `show` command shows a configuration of the current section. It also supports an argument with the relative path (e.g., `show interfaces lo0.0` from the root or `show lo0.0` from the interfaces section). Also, `show ver`, and `show version` gives you the version of the configuration file (or not, who knows?).
- `go` command navigates you to any child section from the current one.
- `top` command without any arguments sets the current path back to the root.
- - `top show` modification allows you to see the full configuration (the configuration of the root). It also supports relative paths as the `show` does.
- - `top go` modification allows you to change the current path to any other possible section.
- `up` command without any arguments sets the current path back to the previous section. It supports a number of sections to return. If the number is bigger than the current depth `up` works as `top`. It also supports `show` instead the number, `up show` does not support any arguments or modificators at this moment.

And some commands are for the CLI-mode:

- `exit` (also, `stop`, `quit`, and `logout`) command to exit.
- `open` command requires two arguments (`open nos filename`):
- - the name of NOS (currently, it supports only `junos` keyword).
- - path and name of a target config file.
- `switch` command to switch among the different contexts, requires the name of the context to switch. Contexts are automatically named `vtyX`.

The `show` command supports the modificators after the `|` symbol. Modificators can be stacked into a pipeline. Nested with the `top`, the `show` supports all the same modificators as without the nesting. There are three types of modificators: leading, passthrough, and terminating. The leading modificator can be placed **only** after the first `|` symbol of the pipeline. In the other words, this is the first modificator in the line. The passthrough modificator can be placed anywhere, and the terminating modificator can be placed **only** as the last one.

- `filter` (*passthrough*) is for filtering the current output line by line. The modificator supports all the powers of Python's regular expressions (the search mode). You can use them with or without `"`, but for sophisticated expressions it's better to use quotes.

	> show | filter "^xe-1/\d/\d{2}$"

	> show protocols l2circuit | filter "neighbor 10.(?:\d{1,3}\.){2}15"

- `wc_filter` (*passthrough*) is for filtering the current output taking into consideration only the names of children sections. In the other words, it allows you to filter sections by their name. The `{` in the section name **must** be omitted. The same RegExp support as for the `filter`.

	> show interfaces | wc_filter "^xe-(?\d{1}/){2}0"

- `count` (*terminating*) is to count the lines.

	> show | count

	> show routing-options | count

- `save` (*terminating*) is for saving the current output to a specified file. The encoding for this file is the same as the encoding of the current context but you can change it with the `set encoding` command.

	> show | save file1.conf

	> show routing-instances | save file2.conf

	> show | filter "address" | save file3.conf

- `stubs` (*leading*) is for showing knobs of the current sections (knob is a command with the `;` symbol in the end). It does not show the nested knobs!

	> show | stubs

	> show system | stubs | count

- `inactive` (*leading*) is for showing all inactive sections and knobs (with them parent sections) starting from this section.

	> show | inactive

	> show protocols bgp | inactive

- `sections` (*leading*) is for showing the names of all child sections that you can visit with the `go` command from the current section.

	> show | sections

	> show interfaces | sections

- `compare` (*leading*) is to compare the current section and its children with another context. To do so you first need to set names for both contexts with the `set name` command. The CLI-mode sets to all contexts their names by default.

	> show | compare cont01

	> show xe-0/0/1 | compare cont01


# Misc

## Issues

Textual is a young and powerful lib. But despite its abilities, some widgets are not good at tasks that Thymus rises. At this time, some hacks are used to draw lengthy configs (i.e., several megabytes) to the screen. Thymus shows you only the two first screens and then after every fourth scroll wheel down event, it appends one screen as a tail.  You can easily notice it by putting the vertical scroll bar to the very end. In this case, there will not be a full config on the screen! That was made intentionally so you can scroll down some output without any side effects of the sub-loading.

The sidebar shows you sections for autocompleting your current input. It works well but can be and will be enhanced later. Also, there are some performance penalties so the number of sections is limited to the current size of the screen.

## What's next

- Configs` analyzing.
- Other NOS`es support.

## Feedback

[Twitter](https://twitter.com/blademd)
[Telegram](https://t.me/blademd)
