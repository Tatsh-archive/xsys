# About

System information script for X-Chat. The old X-Sys plugin (in C) is no longer supported by the author, and has a few bugs due to its age.

Currently this script only supports Linux.

# Installation

Copy `xsys.py` to `~/.xchat2`.

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

- `/sound` only works with PCI if the system is not using ALSA
- `/video` only supports the binary nVidia driver for the moment. Only supports one GPU.
- `/ether` only supports PCI-based ethernet cards
- `/distro` relies upon the `/etc/lsb_release` or `/etc/lsb-release` file existing. If that does not exist, the command only checks for the following distros: Gentoo, RedHat, Slackware, Mandrake, Debian, SuSE, TurboLinux
- `/hwmon` only supports the binary nVidia driver to get the current GPU temperature. Only supports 1 GPU.
