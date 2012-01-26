#!/usr/bin/env python

import os.path
import shutil
import string
import subprocess
import time

from boto.ec2.connection import EC2Connection

TEMP_MOUNT_POINT = '/mnt/solrmigration'
SOLR_DIR = '/opt/solr/panda/solr'

# Prompt for parameters
aws_key = raw_input('Enter your AWS Access Key: ')
secret_key = raw_input('Enter your AWS Secret Key: ')
size_gb = raw_input('How many GB would you like your new volume to be? ')

print 'Connecting'
conn = EC2Connection(aws_key, secret_key)

print 'Identifying running instance'
instance_id = subprocess.check_output(['ec2metadata', '--instance-id']).strip()

reservations = conn.get_all_instances()

instance = None

for r in reservations:
    for i in r.instances:
        if i.id == instance_id:
            instance = i
            break

    if instance:
        break

print 'Creating a new volume'
vol = conn.create_volume(size_gb, instance.placement)

print 'Determining available device path'
ec2_device_name = None
device_path = None

for letter in string.lowercase[6:]:
    ec2_device_name = '/dev/sd%s' % letter
    device_path = '/dev/xvd%s' % letter

    if not os.path.exists(device_path):
        break

print 'Attaching new volume'
vol.attach(instance.id, ec2_device_name) 

while not os.path.exists(device_path):
        time.sleep(1)

print 'Formatting volume'
subprocess.check_call(['mkfs.ext3', device_path])

print 'Creating temporary mount point'
if os.path.exists(TEMP_MOUNT_POINT):
    shutil.rmtree(TEMP_MOUNT_POINT)

os.mkdir(TEMP_MOUNT_POINT)

print 'Mounting volume'
subprocess.check_call(['mount', device_path, TEMP_MOUNT_POINT])

print 'Stopping Solr'
subprocess.call(['service', 'solr', 'stop'])

print 'Copying indexes'
names = os.listdir(SOLR_DIR)

for name in names:
    src_path = os.path.join(SOLR_DIR, name)
    dest_path = os.path.join(TEMP_MOUNT_POINT, name)

    if os.path.isdir(src_path):
        shutil.copytree(src_path, dest_path)
    else:
        shutil.copy2(src_path, dest_path)

print 'Removing old indexes'
shutil.rmtree(SOLR_DIR)

print 'Creating final mount point'
os.mkdir(SOLR_DIR)

print 'Dismounting from temporary mount point'
subprocess.check_call(['umount', TEMP_MOUNT_POINT])

print 'Remounting at final mount point'
subprocess.check_call(['mount', device_path, SOLR_DIR])

print 'Reseting permissions'
subprocess.check_call(['chown', '-R', 'solr:solr', SOLR_DIR])

print 'Restarting Solr'
subprocess.check_call(['service', 'solr', 'start'])

print 'Configuring fstab'
with open('/etc/fstab', 'a') as f:
    f.write('\n%s\t%s\text3\tdefaults,noatime\t0\t0' % (device_path, SOLR_DIR))

