# About

System information script for X-Chat. The old X-Sys plugin (in C) is no longer supported by the author, and has a few bugs due to its age.

# Installation

## HexChat

Copy `xsys.py` to `~/.config/hexchat`.

## X-Chat

Copy `xsys.py` to `~/.xchat2`.

# Hacking

The only commands not implemented are those that store settings: `/xsys2format`, `/playing` (for configuring how the `/np` command should output; colours, etc), `/percentages` (if percentages should be used instead of totals for memory and disk space), and `/npaction`.

For easy testing (instead of having to manually load and unload into X-Chat 2 again and again), test the script using in the command line using `./xsys-cli`. It is only for Python 2.

If you modify the `/np` command, make sure to test it with non-ASCII titled songs (test any UTF-8 encoded text) in X-Chat 2 (not just in the command line). If anything fails, it is probably because `xchat.command()` is expecting a byte string. As such, you may need to `encode()` ([Unicode HOWTO](http://docs.python.org/2/howto/unicode.html)) the string in all stages prior to calling `xchat.command()`.

If you want to send a pull request, check all Python files and fix them to be PEP 8 conformant before doing so.

# Commands

- `/sysinfo` General system information (a combination of several commands)
- `/xsys` Show X-Sys version
- `/cpuinfo` Show CPU name, count of CPU cores, and current speed
- `/sysuptime` Show system uptime in a human readable format
- `/osinfo` Show OS information (similar to `uname` command)
- `/sound` Show all sound cards
- `/netdata` Show current network statistics (transmitted and received)
- `/netstream` Show current network speeds (note that this will freeze X-Chat for 1 second to test)
- `/diskinfo` Show total space and free space
- `/meminfo` Show memory information
- `/video` Show video card information
- `/ether` Show all ethernet adapters
- `/distro` Get distro information
- `/hwmon` Read temperatures from sensors

# Limitations

- Only officially supports Linux
- `/sound` only works with PCI if the system is not using ALSA
- `/video` For binary drivers, only supports the nVidia driver. Otherwise reads PCI data generically and does not determine the slot type.
- `/distro` relies upon the `/etc/lsb_release` or `/etc/lsb-release` file existing. If that does not exist, the command only checks for the following distros: Gentoo, RedHat, Slackware, Mandriva, Debian, SuSE, TurboLinux, Sabayon
- `/hwmon` has limited support for the binary nVidia driver and generic support for recent Intel chipsets
