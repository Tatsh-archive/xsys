#!/usr/bin/python
# -*- coding: utf-8 -*-

import xchat
import platform
import os
import fileinput
import subprocess as sp

from time import sleep
from socket import getfqdn

__module_name__ = "X-Sys Replacement"
__module_version__ = "0.1"
__module_description__ = "X-Sys replacement in Python"


def wrap(word, string):
    return u'' + word + u'[' + string + u']'

# Only for Linux at the moment
linux_PCI_CLASS_NETWORK_ETHERNET = 0x0200


def parse_pci_path_ids(path):
    device_file = os.path.join(path, 'device')
    vendor_file = os.path.join(path, 'vendor')
    finput = fileinput.input([device_file, vendor_file])

    device_id = int(float.fromhex(finput[0].strip('\n')))
    vendor_id = int(float.fromhex(finput[1].strip('\n')))

    fileinput.close()

    return [device_id, vendor_id]


def pci_find_by_class(class_id):
    devices_path = '/sys/bus/pci/devices'
    devices = []

    if os.path.exists(devices_path) is False:
        raise EnvironmentError('Path "%s" must exist' % devices_path)

    for name in os.listdir(devices_path):
        path = os.path.join(devices_path, name)
        class_file = os.path.join(path, 'class')

        if os.path.isdir(path) \
        and os.path.isfile(class_file): # Only top-level
            hex_value = fileinput.input([class_file])[0][:6]
            dev_class_id = float.fromhex(hex_value)
            fileinput.close()

            if dev_class_id == class_id:
                devices.append(parse_pci_path_ids(path))

    return devices


def pci_find_fullname(device_id, vendor_id):
    pci_ids_file = '/usr/share/misc/pci.ids'
    device_name = False

    if os.path.isfile(pci_ids_file) is False:
        return '%x:%x' % (vendor_id, device_id)

    with open(pci_ids_file) as f:
        for line in f:
            if line[0].isspace() is False and ('%x' % vendor_id) in line:
                vendor_name = ' '.join(
                    filter(remove_empty_strings, line.split(' ')[1:]))
                break

        for line in f:
            if ('%x' % device_id) in line:
                device_name = ' '.join(
                    filter(remove_empty_strings, line.split(' ')[1:]))
                break

    if device_name is not False:
        return ('%s %s' % (vendor_name, device_name)).replace('\n', '')

    return '%x:%x' % (vendor_id, device_id)


def remove_empty_strings(value):
    if value.strip().replace('\n', '') == '':
        return False
    return True


def cpuinfo(word, word_eol, userdata):
    def parse_cpu_info():
        try:
            vendor = 'vendor not found'
            freq = 0
            return_value = {'freq': freq, 'vendor': vendor, 'count': 1}

            speed_output = sp.check_output(
                'cat /proc/cpuinfo | grep cpu\ MHz', shell=True).split("\n")
            vendor = sp.check_output('uname -i', shell=True).split("\n")[0]

            return_value['vendor'] = vendor
            multiplier = len(speed_output) - 1  # Last is usually ''
            speed = speed_output[0].split('\t\t: ')[1]
            return_value['freq'] = float(speed)
            return_value['count'] = multiplier
        except CalledProcessError:
            pass
        finally:
            return return_value

    dest = xchat.get_context()
    info = parse_cpu_info()
    cpu_model = platform.processor()
    ghz = info['freq'] > 1000
    output = '%d x %s (%s) @ ' % (info['count'], cpu_model, info['vendor'])

    if ghz:
        info['freq'] /= 1000
        output += '%.2f GHz' % (info['freq'])
    else:
        output += '%.2f MHz' % (info['freq'])

    dest.command('say %s' % wrap('cpu', output))

    return xchat.EAT_ALL

# TODO Handle GiB


def meminfo(word, word_eol, userdata):
    dest = xchat.get_context()

    lines = sp.check_output(
        'cat /proc/meminfo | grep -E "^Mem(Total|Free)|^Cached"',
        shell=True
    ).split("\n")
    total_kb = None
    free_kb = None
    cached_kb = None

    for line in lines:
        parts = line.split(':')

        if len(parts) != 2:
            continue

        value = long(parts[1].strip().split(' ')[0], 10)
        if parts[0] == 'MemTotal':
            total_kb = value
        elif parts[0] == 'MemFree':
            free_kb = value
        elif parts[0] == 'Cached':
            cached_kb = value

        if total_kb is not None \
        and free_kb is not None \
        and cached_kb is not None:
            break

    free_mb = (free_kb / 1024) + (cached_kb / 1024)
    total_mb = total_kb / 1024
    unit = 'MiB'
    output = 'Physical: %.1f %s/%.1f %s free' % (free_mb, unit, total_mb, unit)

    dest.command('say %s' % wrap('memory', output))

    return xchat.EAT_ALL


def diskinfo(word, word_eol, userdata):
    lines = sp.check_output(
        'df -T | grep -E "^/dev/(s|h|x)(d|vd)"', shell=True).split('\n')
    total_free_space = 0
    total_blocks = 0  # 1 KiB blocks

    for line in lines:
        try:
            parts = filter(remove_empty_strings, line.split(' '))
            free_space = long(parts[4])

            total_free_space += free_space
            total_blocks += long(parts[3])
        except IndexError:
            pass

    total_gigabytes = total_blocks / 1024 / 1024
    total_terabytes = total_gigabytes / 1024
    unit = 'GiB'

    total_free_gigabytes = total_free_space / 1024 / 1024
    total_free_terabytes = total_free_gigabytes / 1024 / 1024

    total = total_gigabytes
    free = total_free_gigabytes

    # if total_terabytes > 1:
        # unit = 'TiB'
        # total = total_terabytes
        # free = total_free_terabytes

    dest = xchat.get_context()

    output = 'Total: %.1f %s/%.1f %s free' % (free, unit, total, unit)
    dest.command('say %s' % wrap('disk', output))

    return xchat.EAT_ALL


def video(word, word_eol, userdata):
    nvidia_file = '/proc/driver/nvidia/gpus/0/information'
    output = ''
    model = ''
    bus_type = ''

    if os.path.exists(nvidia_file):
        for line in fileinput.input([nvidia_file]):
            fields = filter(remove_empty_strings, line.split(' '))

            if fields[0] == 'Model:':
                model = ' '.join(fields[1:])
            elif fields[0] == 'Bus' and fields[1] == 'Type:':
                bus_type = ' '.join(fields[2:])

    if model:
        output = '%s' % (model)
        if bus_type:
            output += ' on %s bus' % (bus_type)

    output = output.replace('\n', '')

    if output:
        dest = xchat.get_context()
        dest.command('say %s' % wrap('video', output))

    return xchat.EAT_ALL


def ether(word, word_eol, userdata):
    # TODO USB devices and Bluetooth
    def get_ethernet_devices():
        devices = pci_find_by_class(linux_PCI_CLASS_NETWORK_ETHERNET)
        names = []

        for device_id, vendor_id in devices:
            names.append(pci_find_fullname(device_id, vendor_id))

        return names

    names = get_ethernet_devices()
    output = ', '.join(names)

    if output:
        dest = xchat.get_context()
        dest.command('say %s' % wrap('ether', output))

    return xchat.EAT_ALL

# TODO Non-PCI when not using ALSA


def sound(word, word_eol, userdata):
    names = []
    alsa_sound_card_list_file = '/proc/asound/cards'

    if os.path.isfile(alsa_sound_card_list_file) is False:
        devices = pci_find_by_class(linux_PCI_CLASS_MULTIMEDIA_AUDIO)
        for device_id, vendor_id in devices:
            names.append(pci_find_fullname(device_id, vendor_id))

        output = ', '.join(names)

        if output:
            dest = xchat.get_context()
            dest.command('say %s' % wrap('sound', output))
            return xchat.EAT_ALL

    with open(alsa_sound_card_list_file) as f:
        for line in f:
            if line[0].isdigit() or line[1].isdigit():
                card_name = ''
                pos = line.find(':')
                card_id = long(''.join(
                    filter(remove_empty_strings, line.split(' '))[0]).strip())
                card_name = '%s' % line[(pos + 2):]

                names.append(card_name)

    output = ', '.join(names).replace('\n', '')

    if output:
        dest = xchat.get_context()
        dest.command('say %s' % wrap('sound', output))

    return xchat.EAT_ALL


def parse_netdev(device_name):
    dev_line = None

    with open('/proc/net/dev') as f:
        for line in f:
            stripped_line = line.lstrip()
            if cmp(stripped_line[:len(device_name)], device_name) == 0:
                dev_line = stripped_line
                break

    if dev_line is None:
        raise Exception('Unable to find line for device %s' % device_name)

    pos = dev_line.find(':')
    pos += 1

    line = filter(remove_empty_strings, dev_line[pos:].split(' '))

    bytes_recv = long(line[0])
    bytes_sent = long(line[8])

    return [bytes_recv, bytes_sent]


def netdata(word, word_eol, userdata):
    try:
        device = word[1]
    except IndexError:
        print('You must specify a network device! (e.g.: /netdata eth0)')
        return xchat.EAT_ALL

    try:
        bytes_recv, bytes_sent = parse_netdev(device)
    except:
        print sys.exc_info()
        print('Error calling parse_netdev()')
        return xchat.EAT_ALL

    bytes_recv /= 1024
    bytes_sent /= 1024

    output = '%s %.1f MiB received, %.1f MiB sent' % (
        device, float(bytes_recv / 1024.0), float(bytes_sent / 1024.0))
    dest = xchat.get_context()

    dest.command('say %s' % wrap('netdata', output))

    return xchat.EAT_ALL


def netstream(word, word_eol, userdata):
    recv_suffix = 'B/s'
    sent_suffix = 'B/s'

    try:
        device = word[1]
    except IndexError:
        print('You must specify a network device! (e.g.: /netdata eth0)')
        return

    try:
        bytes_recv, bytes_sent = parse_netdev(device)
    except:
        print sys.exc_info()
        print('Error calling parse_netdev()')
        return xchat.EAT_ALL

    # Original in C
    # struct timespec ts = {1, 0};
    # while(nanosleep(&ts, &ts) < 0);
    sleep(1.0)

    try:
        bytes_recv_p, bytes_sent_p = parse_netdev(device)
    except:
        print sys.exc_info()
        print('Error calling parse_netdev()')
        return xchat.EAT_ALL

    bytes_recv = bytes_recv_p - bytes_recv
    bytes_sent = bytes_sent_p - bytes_sent

    if bytes_recv > 1024:
        bytes_recv /= 1024
        recv_suffix = 'KiB/s'

    if bytes_sent > 1024:
        bytes_sent /= 1024
        sent_suffix = 'KiB/s'

    output = '%s: Receiving %lu %s, Sending %lu %s' % (
        device, bytes_recv, recv_suffix, bytes_sent, sent_suffix)
    dest = xchat.get_context()

    dest.command('say %s' % wrap('netstream', output))

    return xchat.EAT_ALL


def uptime(word, word_eol, userdata):
    def parse_uptime():
        uptime = 0

        with open('/proc/uptime') as f:
            for line in f:
                uptime = float(line.split(' ')[0].strip())
                break

        seconds = uptime % 60
        minutes = (uptime / 60) % 60
        hours = (uptime / 3600) % 24
        days = (uptime / 86400) % 7
        weeks = uptime / 604800

        return [weeks, days, hours, minutes, seconds]

    output = ''

    try:
        weeks, days, hours, minutes, seconds = parse_uptime()
    except:
        print sys.exc_info()
        print('Error calling parse_uptime()')
        return xchat.EAT_ALL

    if minutes != 0 or hours != 0 or days != 0 or weeks != 0:
        if hours != 0 or days != 0 or weeks != 0:
            if days != 0 or weeks != 0:
                if weeks != 0:
                    output = '%dw %dd %dh %dm %ds' % (
                        weeks, days, hours, minutes, seconds)
                else:
                    output = '%dd %dh %dm %ds' % (
                        days, hours, minutes, seconds)
            else:
                output = '%dh %dm %ds' % (hours, minutes, seconds)
        else:
            output = '%dm %ds' % (minutes, seconds)

    if output:
        dest = xchat.get_context()
        dest.command('say %s' % wrap('uptime', output))

    return xchat.EAT_ALL


def osinfo(word, word_eol, userdata):
    kernel = '%s %s %s' % (
        platform.system(), platform.release(), platform.machine())
    output = '%s@%s %s' % (os.environ['USER'], getfqdn(), kernel)
    dest = xchat.get_context()

    xchat.command('say %s' % wrap('osinfo', output))

    return xchat.EAT_ALL


def parse_distro():
    def strpbrk(haystack, char_list):
        try:
            pos = next(i for i, x in enumerate(haystack) if x in char_list)
            return haystack[pos:]
        except:
            return None

    def find_match_char(search, match):
        search = search.lstrip()
        delimiters = [':', '=']
        result = None

        if search.find(match) == search.find(search):
            position = strpbrk(search, delimiters)

            if position is not None:
                position += 1
                result = (search[position:] + '\n').lstrip()

        return result

    def parse_gentoo(make_conf_file):
        keywords = None

        for line in make_conf_file:
            keywords = line.find('ACCEPT_KEYWORDS')

        if keywords == -1:
            return 'Gentoo Linux (stable)'

        keywords = keywords.split('ACCEPT_KEYWORDS=')[1].replace('"', '')

        return 'Gentoo Linux %s' % keywords

    def parse_lsb_release_file(f):
        distro_id = None
        codename = None
        release = None
        for line in f:
            if distro_id is None:
                distro_id = find_match_char(line, 'DISTRIB_ID')
            if codename is None:
                codename = find_match_char(line, 'DISTRIB_CODENAME')
            if release is None:
                release = find_match_char(line, 'DISTRIB_RELEASE')

            if release is not None \
            and distro_id is not None \
            and codename is not None:
                break

        if distro_id is None:
            distro_id = '?'
        if codename is None:
            codename = '?'
        if release is None:
            release = '?'

        return '%s "%s" %s' % (distro_id, codename, release)

    def get_first_line_of_file(f):
        return f[0]

    files_to_parser_functions = [
        ['/etc/lsb_release', parse_lsb_release_file],
        ['/etc/make.conf', parse_gentoo],
        ['/etc/portage/make.conf', parse_gentoo],
        # Prefer lsb-release after make.conf for Gentoo
        ['/etc/lsb-release', parse_lsb_release_file],
        ['/etc/redhat-release', get_first_line_of_file],
        ['/etc/slackware-release', get_first_line_of_file],
        ['/etc/mandrake-release', get_first_line_of_file],
        ['/etc/debian_version', lambda f: 'Debian %s' % f[0]],
        ['/etc/SuSE-release', get_first_line_of_file],
        ['/etc/turbolinux-release', get_first_line_of_file],
    ]

    for release_file_name, parser_callback in files_to_parser_functions:
        try:
            with open(release_file_name) as f:
                return parser_callback(f)
        except:
            pass

    return 'Unknown distro'


def distro(word, word_eol, userdata):
    dest = xchat.get_context()
    dest.command('say %s' % wrap('distro', parse_distro()))
    return xchat.EAT_ALL

# xchat.hook_command('xsys2format', xsys2format)
# xchat.hook_command('playing', playing)
# xchat.hook_command('percentages', percentages)
# xchat.hook_command('npaction', npaction)
# xchat.hook_command('sysinfo', sysinfo)
# xchat.hook_command('xsys', xsys)
xchat.hook_command('cpuinfo', cpuinfo)
xchat.hook_command('sysuptime', uptime)
xchat.hook_command('osinfo', osinfo)
xchat.hook_command('sound', sound)
xchat.hook_command('netdata', netdata)
xchat.hook_command('netstream', netstream)
xchat.hook_command('diskinfo', diskinfo)
xchat.hook_command('meminfo', meminfo)
xchat.hook_command('video', video)
xchat.hook_command('ether', ether)
xchat.hook_command('distro', distro)
# xchat.hook_command('hwmon', hwmon) # TODO Maybe
# xchat.hook_command('np', np)
