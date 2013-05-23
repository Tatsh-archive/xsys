#!/usr/bin/env python
# -*- coding: utf-8 -*-

import xchat
import platform
import os
import fileinput
import subprocess as sp
import sys
import re

from time import sleep
from socket import getfqdn

has_dbus = False

try:
    import dbus
    dbus.SessionBus()
    has_dbus = True
except:
    pass

__module_name__ = "X-Sys Modernised"
__module_version__ = "1.0"
__module_description__ = "X-Sys replacement in Python"

PCI_CLASS_NETWORK_ETHERNET = 0x0200
PCI_CLASS_NETWORK_ETHERNET_WIFI = 0x0280  # Correct?
PCI_CLASS_MULTIMEDIA_AUDIO_ALT = 0x0401
PCI_CLASS_MULTIMEDIA_AUDIO = 0x0403
PCI_CLASS_DISPLAY = 0x0300

# http://en.wikipedia.org/wiki/Universal_Serial_Bus#Device_classes
USB_CLASS_NETWORK = 0x02
USB_CLASS_BLUETOOTH = 0xe0
# USB adapter from Apple, and Bluetooth internal (which is via USB)
# Technically this is for all other devices
# The iPhone with Hotspot support also falls under this class
USB_CLASS_NETWORK_GENERIC = 0xff

# TODO Setting by /percentages command
percentages = False


def wrap(word, string):
    return (u'' + word + u'[' + string + u']').encode(
        'utf-8',
        errors='replace')


# Only for Linux at the moment
def parse_pci_path_ids(path):
    device_file = os.path.join(path, 'device')
    vendor_file = os.path.join(path, 'vendor')
    finput = fileinput.input([device_file, vendor_file])

    device_id = int(float.fromhex(finput[0].strip('\n')))
    vendor_id = int(float.fromhex(finput[1].strip('\n')))

    fileinput.close()

    return [device_id, vendor_id]


def parse_usb_path_ids(path):
    device_file = os.path.join(path, 'idProduct')
    vendor_file = os.path.join(path, 'idVendor')
    finput = fileinput.input([device_file, vendor_file])

    device_id = int(float.fromhex('0x' + finput[0].strip('\n')))
    vendor_id = int(float.fromhex('0x' + finput[1].strip('\n')))

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
                and os.path.isfile(class_file):  # Only top-level
            hex_value = fileinput.input([class_file])[0][:6]
            dev_class_id = float.fromhex(hex_value)
            fileinput.close()

            if dev_class_id == class_id:
                devices.append(parse_pci_path_ids(path))

    return devices


def usb_find_by_class(class_id):
    devices_path = '/sys/bus/usb/devices'
    devices = []

    if os.path.exists(devices_path) is False:
        raise EnvironmentError('Path "%s" must exist' % devices_path)

    for name in os.listdir(devices_path):
        path = os.path.join(devices_path, name)
        class_file = os.path.join(path, 'bDeviceClass')

        if os.path.isdir(path) \
                and os.path.isfile(class_file):  # Only top-level
            hex_value = '0x' + fileinput.input([class_file])[0]
            dev_class_id = float.fromhex(hex_value)
            fileinput.close()

            if dev_class_id == class_id:
                devices.append(parse_usb_path_ids(path))

    return devices


def get_device_fullname(device_id, vendor_id, ids_file):
    device_name = False
    vendor_name = 'Unknown vendor'

    if os.path.isfile(ids_file) is False:
        return '%x:%x' % (vendor_id, device_id)

    with open(ids_file) as f:
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


def pci_find_fullname(device_id, vendor_id):
    pci_ids_file = '/usr/share/misc/pci.ids'
    return get_device_fullname(device_id, vendor_id, pci_ids_file)


def usb_find_fullname(device_id, vendor_id):
    usb_ids_file = '/usr/share/misc/usb.ids'
    return get_device_fullname(device_id, vendor_id, usb_ids_file)


def remove_empty_strings(value):
    if value.strip().replace('\n', '') == '':
        return False
    return True


def sysinfo_cpuinfo():
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

    info = parse_cpu_info()
    cpu_model = platform.processor()
    ghz = info['freq'] > 1000
    output = '%d x %s (%s) @ ' % (info['count'], cpu_model, info['vendor'])

    if ghz:
        info['freq'] /= 1000
        output += '%.2f GHz' % (info['freq'])
    else:
        output += '%.2f MHz' % (info['freq'])

    return output


def cpuinfo(word, word_eol, userdata):
    dest = xchat.get_context()
    dest.command('say %s' % wrap('cpu', sysinfo_cpuinfo()))
    return xchat.EAT_ALL


def sysinfo_meminfo():
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

    return output


def meminfo(word, word_eol, userdata):
    dest = xchat.get_context()
    dest.command('say %s' % wrap('memory', sysinfo_meminfo()))
    return xchat.EAT_ALL


def sysinfo_diskinfo():
    def pretty_freespace(free_k, total_k):
        def percentage(free, total):
            result = free * 1000 / total
            return result / 10.0

        i = 0
        bytesize = 'B'
        quantities = ['KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB']
        result = ''
        free_space = free_k
        total_space = total_k

        if total_k == 0:
            return '%s: none' % desc

        while total_space > 1023 and i < 8:
            i += 1
            bytesize = quantities[i]
            free_space /= 1024.0
            total_space /= 1024.0

        if percentages:
            result = '%.2f %s, %.1f%% total space free' % (
                total_space,
                bytesize,
                percentage(free_k, total_k))
        else:
            result = '%.2f %s used / %.2f %s total' % (
                free_space,
                bytesize,
                total_space,
                bytesize)

        return result

    lines = sp.check_output('df -k -l -P', shell=True).split('\n')
    total_k = 0
    free_k = 0

    for line in lines:
        try:
            if line.find('/dev/loop') != -1:
                continue

            if line[0].isalpha():
                continue
        except:
            continue

        parts = filter(remove_empty_strings, line.split(' '))
        total_k += long(parts[1])
        free_k += long(parts[2])

    return pretty_freespace(free_k, total_k)


def diskinfo(word, word_eol, userdata):
    dest = xchat.get_context()
    dest.command('say %s' % wrap('disk', sysinfo_diskinfo()))
    return xchat.EAT_ALL


# TODO Support getting slot type for other video cards (most likely
#   proprietary only)
def sysinfo_video():
    has_nvidia_proprietary = False

    def parse_nvidia():
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

        has_nvidia_proprietary = True

        return output

    def parse_pci():
        devices = pci_find_by_class(PCI_CLASS_DISPLAY)
        names = []
        nvidia_vendor_id = 0x10de

        for device_id, vendor_id in devices:
            if has_nvidia_proprietary and vendor_id == nvidia_vendor_id:
                continue

            names.append(pci_find_fullname(device_id, vendor_id))

        return names

    nvidia_output = parse_nvidia()
    has_nvidia_proprietary = nvidia_output != ''

    output = filter(remove_empty_strings, [nvidia_output] + parse_pci())
    output = ', '.join(output).replace('\n', '')

    return output


def video(word, word_eol, userdata):
    dest = xchat.get_context()
    output = sysinfo_video()

    if output:
        dest.command('say %s' % wrap('video', output))
    else:
        dest.command('say %s' % wrap('video', 'Unknown video card'))

    return xchat.EAT_ALL


def ether(word, word_eol, userdata):
    # TODO Add iPhone hotspot (find ipheth)
    def get_ethernet_devices():
        devices = pci_find_by_class(PCI_CLASS_NETWORK_ETHERNET)
        devices += pci_find_by_class(PCI_CLASS_NETWORK_ETHERNET_WIFI)
        usb_devices = usb_find_by_class(USB_CLASS_NETWORK)
        usb_devices += usb_find_by_class(USB_CLASS_NETWORK_GENERIC)
        usb_devices += usb_find_by_class(USB_CLASS_BLUETOOTH)
        names = []

        for device_id, vendor_id in devices:
            names.append(pci_find_fullname(device_id, vendor_id))

        for device_id, vendor_id in usb_devices:
            names.append(usb_find_fullname(device_id, vendor_id))

        return names

    names = get_ethernet_devices()
    output = ', '.join(names)

    if output:
        dest = xchat.get_context()
        dest.command('say %s' % wrap('ether', output))
    else:
        xchat.prnt('No ethernet devices found')

    return xchat.EAT_ALL


# TODO Non-PCI when not using ALSA
def sysinfo_sound():
    names = []
    alsa_sound_card_list_file = '/proc/asound/cards'

    if os.path.isfile(alsa_sound_card_list_file) is False:
        classes = [
            PCI_CLASS_MULTIMEDIA_AUDIO,
            PCI_CLASS_MULTIMEDIA_AUDIO_ALT
        ]

        for class_id in classes:
            devices = pci_find_by_class(class_id)
            for device_id, vendor_id in devices:
                names.append(pci_find_fullname(device_id, vendor_id))

        output = ', '.join(names)

        if output:
            dest = xchat.get_context()
            dest.command('say %s' % wrap('sound', output))
            return xchat.EAT_ALL

    usb_no_name_regex = ('(?P<prefix>.*)USB\sDevice\s0x(?P<vendor_id>'
                         '[\da-f]{3,4})\:0x(?P<device_id>[\da-f]{3,4})')

    with open(alsa_sound_card_list_file) as f:
        for line in f:
            if line[0].isdigit() or line[1].isdigit():
                card_name = ''
                pos = line.find(':')
                card_id = long(''.join(
                    filter(remove_empty_strings, line.split(' '))[0]).strip())
                card_name = '%s' % line[(pos + 2):]
                match = re.search(usb_no_name_regex, card_name)

                if match is not None:
                    dictionary = match.groupdict()
                    prefix = dictionary['prefix']
                    vendor_id = float.fromhex('0x' + dictionary['vendor_id'])
                    vendor_id = int(vendor_id)
                    device_id = float.fromhex('0x' + dictionary['device_id'])
                    device_id = int(device_id)

                    card_name = (prefix +
                                 usb_find_fullname(device_id, vendor_id))

                names.append(card_name)

    output = ', '.join(names).replace('\n', '')

    return output


def sound(word, word_eol, userdata):
    dest = xchat.get_context()
    output = sysinfo_sound()

    if output:
        dest.command('say %s' % wrap('sound', output))
    else:
        xchat.prnt('No sound cards found')

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
        xchat.prnt('You must specify a network device! (e.g.: /netdata eth0)')
        return xchat.EAT_ALL

    try:
        bytes_recv, bytes_sent = parse_netdev(device)
    except:
        # print sys.exc_info()
        xchat.prnt('Error calling parse_netdev()')
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
        xchat.prnt('You must specify a network device! (e.g.: /netdata eth0)')
        return

    try:
        bytes_recv, bytes_sent = parse_netdev(device)
    except:
        #print(sys.exc_info())
        xchat.prnt('Error calling parse_netdev()')
        return xchat.EAT_ALL

    # Original in C
    # struct timespec ts = {1, 0};
    # while(nanosleep(&ts, &ts) < 0);
    sleep(1.0)

    try:
        bytes_recv_p, bytes_sent_p = parse_netdev(device)
    except:
        #print sys.exc_info()
        xchat.prnt('Error calling parse_netdev()')
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
        #print sys.exc_info()
        xchat.prnt('Error calling parse_uptime()')
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
    else:
        xchat.prnt('Could not get uptime')

    return xchat.EAT_ALL


def sysinfo_osinfo():
    kernel = '%s %s %s' % (
        platform.system(), platform.release(), platform.machine())
    return '%s@%s %s' % (os.environ['USER'], getfqdn(), kernel)


def osinfo(word, word_eol, userdata):
    dest = xchat.get_context()
    dest.command('say %s' % wrap('osinfo', sysinfo_osinfo()))
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
            if keywords != -1:
                break

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
        ['/etc/sabayon-release', get_first_line_of_file],
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


def xsys(word, word_eol, userdata):
    dest = xchat.get_context()
    dest.command('me is using %s v%s (https://github.com/Tatsh/%s)' % (
        __module_name__,
        __module_version__,
        __module_name__.split(' ')[0].replace('-', '').lower())
    )
    return xchat.EAT_ALL


def sysinfo(word, word_eol, userdata):
    dest = xchat.get_context()
    output = []

    output.append(wrap('os', sysinfo_osinfo()))
    output.append(wrap('distro', parse_distro()))
    output.append(wrap('cpu', sysinfo_cpuinfo()))
    output.append(wrap('mem', sysinfo_meminfo()))
    output.append(wrap('disk', sysinfo_diskinfo()))
    output.append(wrap('video', sysinfo_video()))
    output.append(wrap('sound', sysinfo_sound()))

    dest.command('say %s' % ' '.join(output))

    return xchat.EAT_ALL


def now_playing_cb(word, word_eol, userdata):
    session_bus = dbus.SessionBus()
    clementine_keys = [
        'org.mpris.MediaPlayer2.clementine',
        'org.mpris.clementine'
    ]
    dest = xchat.get_context()

    for key in clementine_keys:
        try:
            proxy = session_bus.get_object(key, '/Player')
            data = proxy.GetMetadata()

            format_str = u'%s - %s'
            args = (
                data['artist'],
                data['title'],
            )

            try:
                year = data['year']
                format_str += ' (%d)'
                args += (data['year'],)
            except:
                # print sys.exc_info()
                pass

            try:
                output = 'say %s' % wrap('np', format_str % args)
                dest.command(output)
            except:
                # print sys.exc_info()
                pass

            return xchat.EAT_ALL
        except:
            # print sys.exc_info()
            pass

    xchat.prnt('You do not have a supported player running or it is currently '
               'not playing a file')

    return xchat.EAT_ALL


def sysinfo_hwmon():
    def parse_nvidia_gpu_core_temp():
        command_line = ('nvidia-settings -q GPUCoreTemp 2>&1 |'
                        'grep Attribute |'
                        'awk "{ print \$4 }"')
        return int(sp.check_output(command_line, shell=True).strip('.\n'))

    def parse_mobo_and_cpu_temp_lm_sensors():
        lines = sp.check_output('sensors', shell=True).strip().split('\n')
        i = 0
        j = 0
        length = len(lines)
        info = {}

        while i < length:
            if lines[i].strip() == '':
                i += 1
                continue

            device_name = lines[i].strip()

            i += 1
            adapter_name = lines[i].strip()[9:]

            info[device_name] = {
                'adapter_type': adapter_name,
                'temps': []
            }

            j = i
            while j < length:
                if lines[j].strip() == '':
                    j += 1
                    break

                regex = ('^(temp|Core\s?)' +
                         '(?P<index>\d)\:\s+(?P<temp>[\+\-]\d+\.\d+°C)(?' +
                         ':\s+\(.*\)\s+sensor\s+\=\s+(?P<sensor>\w+))?')

                matches = re.search(regex, lines[j])

                if matches is not None:
                    dictionary = matches.groupdict()
                    sensor = dictionary['sensor']

                    if sensor == 'disabled':
                        j += 1
                        continue

                    info[device_name]['temps'].append(
                        dictionary['temp'].lstrip('+'))

                j += 1

            i = j

        return info

    gpu_temp = None
    lm_sensors_info = None

    try:
        gpu_temp = parse_nvidia_gpu_core_temp()
    except:
        pass

    try:
        lm_sensors_info = parse_mobo_and_cpu_temp_lm_sensors()
    except:
        print sys.exc_info()
        pass

    return [lm_sensors_info, gpu_temp]


def hwmon(word, word_eol, userdata):
    lm_sensors_info, gpu_temp = sysinfo_hwmon()
    output = []

    if lm_sensors_info is None and gpu_temp is None:
        xchat.prnt('No monitoring sensors detected')
        return xchat.EAT_ALL

    if gpu_temp is not None:
        output.append(u'gpu:: temp0: %d\xb0C' % gpu_temp)

    if lm_sensors_info is not None:
        for device_name in lm_sensors_info:
            temps = lm_sensors_info[device_name]['temps']
            temp_output = []
            i = 0

            if len(temps):
                for temp in temps:
                    add = ('temp%d: %s' % (i, temp)).decode('utf-8')
                    temp_output.append(add)
                    i += 1

                output.append(device_name + ':: ' + ', '.join(temp_output))

    output = '; '.join(output)

    if output:
        dest = xchat.get_context()
        output = 'say %s' % wrap('sensor', output)
        dest.command(output)
    else:
        xchat.prnt('No monitoring sensors detected')

    return xchat.EAT_ALL


# xchat.hook_command('xsys2format', xsys2format)
# xchat.hook_command('playing', playing)
# xchat.hook_command('percentages', percentages)
# xchat.hook_command('npaction', npaction)
xchat.hook_command('sysinfo', sysinfo)
xchat.hook_command('xsys', xsys)
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
xchat.hook_command('hwmon', hwmon)

if has_dbus:
    xchat.hook_command('np', now_playing_cb)
    xchat.prnt('DBus is available. /np command is enabled')
