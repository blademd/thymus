
![thymus_default_screen](https://github.com/blademd/thymus/assets/1499024/cce6e2e8-02f1-4d46-82c6-daabf51e3d66)


# Thymus

[Thymus](https://en.wikipedia.org/wiki/Thymus_(plant)) — is a config browser. Thymus does not require a connection to any network device (but it can be used itself over SSH from a remote machine). You just need to save a configuration file, open it anytime, and navigate through it. Thymus mimics to CLI of a selected platform.

Thymus supports:

* Juniper JunOS (and probably other JunOS-like systems, e.g. SR-OS **with** MD-CLI)
* Cisco IOS/IOS-XE/NX-OS (and probably other IOS-like systems)
* Arista EOS

*This is the early alpha version! So some glitches can be appearing.*

<details>
	<summary>Screenshots</summary>
	<hr>

 JunOS context screen

 ![thymus_junos_example](https://github.com/blademd/thymus/assets/1499024/e7b0afe9-2b0d-472b-8c6e-098a5fa1dd53)

 IOS context screen

 ![thymus_ios_example](https://github.com/blademd/thymus/assets/1499024/0dfe16c1-2e79-4175-9ca2-fea5882f176b)

 Compare/diff between two configs (JunOS is just as an example)

 ![thymus_junos_compare_example](https://github.com/blademd/thymus/assets/1499024/81b4b4fd-c1cb-4fe8-8e51-f8c435a71025)


</details>

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

Please, refer to [Wiki](https://github.com/blademd/thymus/wiki).

## Feedback

[Twitter](https://twitter.com/blademd)
[Telegram](https://t.me/blademd)
