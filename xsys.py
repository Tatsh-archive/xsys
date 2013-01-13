#!/usr/bin/python
# -*- coding: utf-8 -*-

import xchat
import platform, os, fileinput
import subprocess as sp

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

  if os.path.exists(devices_path) == False:
    raise EnvironmentError('Path "%s" must exist' % devices_path)

  for name in os.listdir(devices_path):
    path = os.path.join(devices_path, name)
    class_file = os.path.join(path, 'class')

    if os.path.isdir(path) and os.path.isfile(class_file): # Only top-level
      dev_class_id = float.fromhex(fileinput.input([class_file])[0][:6])
      fileinput.close()

      if dev_class_id == class_id:
        devices.append(parse_pci_path_ids(path))

  return devices

def pci_find_fullname(device_id, vendor_id):
  pci_ids_file = '/usr/share/misc/pci.ids'
  device_name = False

  if os.path.isfile(pci_ids_file) == False:
    return '%x:%x' % (vendor_id, device_id)

  with open(pci_ids_file) as f:
    for line in f:
      if line[0].isspace() == False and ('%x' % vendor_id) in line:
        vendor_name = ' '.join(filter(remove_empty_strings, line.split(' ')[1:]))
        break

    for line in f:
      if ('%x' % device_id) in line:
        device_name = ' '.join(filter(remove_empty_strings, line.split(' ')[1:]))
        break

  if device_name != False:
    return ('%s %s' % (vendor_name, device_name)).replace('\n', '')

  return '%x:%x' % (vendor_id, device_id)

def parse_cpu_info():
  try:
    vendor = 'vendor not found'
    freq = 0
    return_value = {'freq': freq, 'vendor': vendor, 'count': 1}

    speed_output = sp.check_output('cat /proc/cpuinfo | grep cpu\ MHz', shell=True).split("\n")
    vendor = sp.check_output('uname -i', shell=True).split("\n")[0]

    return_value['vendor'] = vendor
    multiplier = len(speed_output) - 1 # Last is usually ''
    speed = speed_output[0].split('\t\t: ')[1]
    return_value['freq'] = float(speed)
    return_value['count'] = multiplier
  except CalledProcessError:
    pass
  finally:
    return return_value

def cpuinfo(word, word_eol, userdata):
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

  lines = sp.check_output('cat /proc/meminfo | grep -E "^Mem(Total|Free)"', shell=True).split("\n")
  total_kb = 0
  free_kb = 0

  for line in lines:
    parts = line.split(':')

    if len(parts) != 2:
      continue

    value = long(parts[1].strip().split(' ')[0], 10)
    if parts[0] == 'MemTotal':
      total_kb = value
    elif parts[0] == 'MemFree':
      free_kb = value

    if total_kb != 0 and free_kb != 0:
      break

  free_mb = free_kb / 1024
  total_mb = total_kb / 1024
  unit = 'MiB'
  output = 'Physical: %.1f %s/%.1f %s free' % (free_mb, unit, total_mb, unit)

  dest.command('say %s' % wrap('memory', output))

  return xchat.EAT_ALL

def remove_empty_strings(value):
  if value.strip().replace('\n', '') == '':
    return False
  return True

def diskinfo(word, word_eol, userdata):
  lines = sp.check_output('df -T | grep -E "^/dev/(s|h|x)(d|vd)"', shell=True).split('\n')
  total_free_space = 0
  total_blocks = 0 # 1 KiB blocks

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

  #if total_terabytes > 1:
    #unit = 'TiB'
    #total = total_terabytes
    #free = total_free_terabytes

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

# TODO USB devices and Bluetooth
def get_ethernet_devices():
  devices = pci_find_by_class(linux_PCI_CLASS_NETWORK_ETHERNET)
  names = []

  for device_id, vendor_id in devices:
    names.append(pci_find_fullname(device_id, vendor_id))

  return names

def ether(word, word_eol, userdata):
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

  if os.path.isfile(alsa_sound_card_list_file) == False:
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
        card_id = long(''.join(filter(remove_empty_strings, line.split(' '))[0]).strip())
        card_name = '%s' % line[(pos + 2):]

        names.append(card_name)

  output = ', '.join(names).replace('\n', '')

  if output:
    dest = xchat.get_context()
    dest.command('say %s' % wrap('sound', output))

  return xchat.EAT_ALL

#xchat.hook_command('sysinfo', sysinfo)
#xchat.hook_command('xsys2format', xsys2format)
#xchat.hook_command('playing', playing)
#xchat.hook_command('npaction', npaction)
#xchat.hook_command('percentages', percentages)
xchat.hook_command('cpuinfo', cpuinfo)
xchat.hook_command('meminfo', meminfo)
xchat.hook_command('diskinfo', diskinfo)
xchat.hook_command('sound', sound)
xchat.hook_command('video', video)
#xchat.hook_command('np', np)
#xchat.hook_command('netdata', netdata)
#xchat.hook_command('netstream', netstream)
xchat.hook_command('ether', ether)
