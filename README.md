# Thymus

[Thymus](https://en.wikipedia.org/wiki/Thymus_(plant)) — is a config browser. Thymus does not require a connection to any network device (but it can be used itself over SSH from a remote machine). You just need to save a configuration file, open it anytime, and navigate through it. Thymus mimics to CLI of a selected platform.

Thymus supports:

* Juniper JunOS (and probably other JunOS-like systems, e.g. SR-OS **with** MD-CLI)
* Cisco IOS/IOS-XE (and probably other IOS-like systems)
* Arista EOS

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

## Documentation

*In progress...*

## Feedback

[Twitter](https://twitter.com/blademd)
[Telegram](https://t.me/blademd)
