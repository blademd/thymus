
![thymus_default_screen](https://github.com/blademd/thymus/assets/1499024/7b68e7bd-0ea1-49fc-9503-e24254d2c014)


# Thymus

[Thymus](https://en.wikipedia.org/wiki/Thymus_(plant)) — is a config browser and editor. Thymus understands the context of a network configuration file compared to popular text editors. It mimics the CLI of a selected platform. That allows you to navigate, display, and edit selected configuration parts based on their paths just like in your favorite network operation system. You can save edited versions many times, creating a history log. Thymus supports the diff among them and can roll back to any saved version.

Thymus does not require a connection to any network device but it can fetch a configuration from a remote machine via Telnet or SSH. Also, it can be used over SSH from a remote machine.

Thymus supports:

* Juniper JunOS (and probably other JunOS-like systems, e.g. SR-OS **with** MD-CLI)
* Cisco IOS/IOS-XE/NX-OS/XR-OS (and probably other IOS-like systems)
* Arista EOS

<details>
	<summary>Screenshots</summary>
	<hr>

 JunOS context screen

 ![thymus_junos_example](https://github.com/blademd/thymus/assets/1499024/de5709b0-44d4-4490-8a5b-c8f59dfb3ff9)

 IOS context screen

 ![thymus_ios_example](https://github.com/blademd/thymus/assets/1499024/51375ef1-f912-44eb-8432-13855f5d3920)

 Compare/diff between two configs (JunOS is just as an example)

 ![thymus_junos_compare_example](https://github.com/blademd/thymus/assets/1499024/a1f1cbbe-f45b-4830-bd58-fcccddcb79ca)


</details>

## Installation

Use `pip` or `pipx` to install the package (e.g., `pip install thymus` or `pipx install thymus`). Requires Python **3.9**!

## Operations

Thymus operates in **TUI-based** mode thanks to the [Textual](https://textual.textualize.io/) library. This mode draws the full-scale user interface in your console with mouse support. From the Textual documentation:

	> On modern terminal software (installed by default on most systems), Textual apps can use **16.7 million** colors with mouse support and smooth flicker-free animation. A powerful layout engine and re-usable components makes it possible to build apps that rival the desktop and web experience.

	> Textual runs on Linux, macOS, Windows and probably any OS where Python also runs.


To run Thymus use the command:
```
python -m thymus
```

## Documentation

Please, refer to [Wiki](https://github.com/blademd/thymus/wiki).

## Feedback

[Telegram](https://t.me/blademd)
