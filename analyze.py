#!/usr/bin/python

# libs
import re
import sys
import datetime
import time
import pickle

# config
timestamp_timeout = 60*60*24   # 1 day
dump_filename = '/tmp/pla.tmp' # BTW external tool must guarantee we're the only instance
input_filename = sys.argv[1]
input_fileid = sys.argv[2]

### functions

# 3-char code for bounced type
def bouncedline2status(line):
  matchObj = re.search(r' said: ([0-9]{3})[ \-]', line)
  if matchObj:
    return matchObj.group(1)
  for pattern, abbrev in [ \
    [r'Name service error', 'DNS'], \
    [r'cannot append message to file', 'CAF'], \
    [r'loops back to myself', 'LBM'], \
  ]:
    if pattern in line:
      return abbrev
  return 'UNK'

# code for status type
def line2status(line):
  for st in ['status=deferred', 'status=sent']:
    if ' ' + st + ' ' in line:
      return st
  for st in ['status=bounced']:
    if ' ' + st + ' ' in line:
      return st + '_' + bouncedline2status(line)
  return None

### main

# initial state
hashes = {}
results = {}
last_byte_processed = 0

# try to unserialize
try:
  dump_file = open(dump_filename, 'r');
  prev = pickle.load(dump_file)
  if prev['fileid'] == input_fileid:
    hashes = prev['hashes']
    results = prev['results']
    last_byte_processed = prev['last_byte_processed']
except (pickle.UnpicklingError, IOError, EOFError):
  pass

# walk file lines
last_timestamp = 0
log_file = open(sys.argv[1], 'r')
log_file.seek(last_byte_processed)
for line in log_file:
  last_byte_processed += len(line)
  # fill empty values ti have at least 12 values
  parts = line.split() + ['' for i in range(0,12)]
  # standard fields
  # fucking logs do not contain year. todo: guess
  last_timestamp = timestamp = time.mktime(datetime.datetime.strptime('2012 ' + ' '.join(parts[0:3]), '%Y %b %d %H:%M:%S').timetuple())
  hash = parts[5]
  # remember info about this hash
  if parts[6:9] == ['warning:', 'header', 'X-Msg-Type-Id:']:
    hashes[hash] = {'type_id': parts[9], 'state': 'in_process', 'timestamp': timestamp}
  # if it is a known non-finalized hash
  if hash in hashes and hashes[hash]['state'] in ['in_process', 'status=deferred']:
    status = line2status(line)
    if status:
      # update but do not finalize
      if status in ['status=deferred']:
        hashes[hash]['state'] = status
        hashes[hash]['timestamp'] = timestamp
      # finalize hash, save into results
      if status.split('_')[0] in ['status=sent', 'status=bounced']:
        key = hashes[hash]['type_id'] + ' ' + status
        results[key] = results.get(key, 0) + 1
        del hashes[hash]
# clear hashes that have no chance to be finalized
hashes_recent = dict(filter(lambda item: item[1]['timestamp'] > last_timestamp - timestamp_timeout, hashes.items()))

# dump staqte
dump_file = open(dump_filename, 'w');
pickle.dump({'hashes': hashes_recent, 'results': results, 'last_byte_processed': last_byte_processed, 'fileid': input_fileid}, dump_file)

# write results on unfinalized hashes
for i in hashes:
  key = hashes[i]['type_id'] + ' ' + hashes[i]['state']
  results[key] = results.get(key, 0) + 1

# print results
for i in results:
  print i, ' ', results[i]

