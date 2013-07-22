import os, sys

def memoryUsage():
    result = dict()

    for l in [l.split(':') for l in os.popen('vm_stat').readlines()[1:8]]:
        result[l[0].strip(' "').replace(' ', '_').lower()] = int(l[1].strip('.\n '))
        
    return result

print memoryUsage()
