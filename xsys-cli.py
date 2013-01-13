#!/usr/bin/python2
# -*- coding: utf-8 -*-

import platform, os, fileinput, sys
import subprocess as sp

from time import sleep

__module_name__ = "X-Sys Replacement"
__module_version__ = "0.1"
__module_description__ = "X-Sys replacement in Python"

def wrap(word, string):
  return u'' + word + u'[' + string + u']'

# Only for Linux at the moment
linux_PCI_CLASS_NETWORK_ETHERNET = 0x0200
# linux_PCI_CLASS_MULTIMEDIA_AUDIO = 0x0401
linux_PCI_CLASS_MULTIMEDIA_AUDIO = 0x0403

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

def cpuinfo():
  info = parse_cpu_info()
  cpu_model = platform.processor()
  ghz = info['freq'] > 1000
  output = '%d x %s (%s) @ ' % (info['count'], cpu_model, info['vendor'])

  if ghz:
    info['freq'] /= 1000
    output += '%.2f GHz' % (info['freq'])
  else:
    output += '%.2f MHz' % (info['freq'])

  print('say %s' % wrap('cpu', output))


# TODO Handle GiB
def meminfo():
  lines = sp.check_output('cat /proc/meminfo | grep -E "^Mem(Total|Free)|^Cached"', shell=True).split("\n")
  total_kb = 0
  free_kb = 0
  cached_kb = 0

  for line in lines:
    parts = line.split(':')

    if len(parts) != 2:
      continue # Bad line

    value = long(parts[1].strip().split(' ')[0], 10)
    if parts[0] == 'MemTotal':
      total_kb = value
    elif parts[0] == 'MemFree':
      free_kb = value
    elif parts[0] == 'Cached':
      cached_kb = value

    if total_kb != 0 and free_kb != 0 and cached_kb != 0:
      break

  free_mb = (free_kb / 1024) + (cached_kb / 1024)
  total_mb = total_kb / 1024
  unit = 'MiB'
  output = 'Physical: %.1f %s/%.1f %s free' % (free_mb, unit, total_mb, unit)

  print('say %s' % wrap('memory', output))


def remove_empty_strings(value):
  if value.strip().replace('\n', '') == '':
    return False
  return True

def diskinfo():
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

  #if (total_terabytes > 1):
    #unit = 'TiB'
    #total = total_terabytes
    #free = total_free_terabytes


  output = 'Total: %.1f %s/%.1f %s free' % (free, unit, total, unit)
  print('say %s' % wrap('disk', output))

def video():
  nvidia_file = '/proc/driver/nvidia/gpus/0/information'
  output = ''
  model = ''
  bus_type = ''

  if (os.path.exists(nvidia_file)):
    for line in fileinput.input([nvidia_file]):
      fields = filter(remove_empty_strings, line.split(' '))

      if (fields[0] == 'Model:'):
        model = ' '.join(fields[1:])
      elif (fields[0] == 'Bus' and fields[1] == 'Type:'):
        bus_type = ' '.join(fields[2:])

  if model:
    output = '%s' % (model)
    if bus_type:
      output += ' on %s bus' % (bus_type)

  output = output.replace('\n', '')

  if output:
    print('say %s' % wrap('video', output))

def get_ethernet_devices():
  devices = pci_find_by_class(linux_PCI_CLASS_NETWORK_ETHERNET)
  names = []

  for device_id, vendor_id in devices:
    names.append(pci_find_fullname(device_id, vendor_id))

  return names

def ether():
  print('say %s' % wrap('ethernet', ', '.join(get_ethernet_devices())))

# TODO Non-PCI when not using ALSA
def sound():
  names = []
  alsa_sound_card_list_file = '/proc/asound/cards'

  if os.path.isfile(alsa_sound_card_list_file) == False:
    devices = pci_find_by_class(linux_PCI_CLASS_MULTIMEDIA_AUDIO)
    for device_id, vendor_id in devices:
      names.append(pci_find_fullname(device_id, vendor_id))

    output = ', '.join(names)

    if output:
      print('say %s' % wrap('sound', output))
      return

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
    print('say %s' % wrap('sound', output))

def parse_netdev(device_name):
  dev_line = None

  with open('/proc/net/dev') as f:
    for line in f:
      stripped_line = line.lstrip()
      if cmp(stripped_line[:len(device_name)], device_name) == 0:
        dev_line = stripped_line
        break

  if dev_line == None:
    raise Exception('Unable to find line for device %s' % device_name)

  pos = dev_line.find(':')
  pos += 1

  line = filter(remove_empty_strings, dev_line[pos:].split(' '))

  bytes_recv = long(line[0])
  bytes_sent = long(line[8])

  return [bytes_recv, bytes_sent]

def netdata(word):
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
    return

  bytes_recv /= 1024
  bytes_sent /= 1024

  output = '%s %.1f MiB received, %.1f MiB sent' % (device, float(bytes_recv/1024.0), float(bytes_sent/1024.0))

  print('say %s' % wrap('netdata', output))

def netstream(word):
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
    return

  # Original in C
  # struct timespec ts = {1, 0};
  # while(nanosleep(&ts, &ts) < 0);
  sleep(1.0)

  try:
    bytes_recv_p, bytes_sent_p = parse_netdev(device)
  except:
    print sys.exc_info()
    print('Error calling parse_netdev()')
    return

  bytes_recv = bytes_recv_p - bytes_recv
  bytes_sent = bytes_sent_p - bytes_sent

  if bytes_recv > 1024:
    bytes_recv /= 1024
    recv_suffix = 'KiB/s'

  if bytes_sent > 1024:
    bytes_sent /= 1024
    sent_suffix = 'KiB/s'

  output = '%s: Receiving %lu %s, Sending %lu %s' % (device, bytes_recv, recv_suffix, bytes_sent, sent_suffix)

  print('say %s' % wrap('netstream', output))

  return

cpuinfo()
meminfo()
diskinfo()
ether()
netdata(['', 'eth0'])
sound()
video()
netstream(['', 'eth0'])
