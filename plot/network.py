#!/usr/bin/env python3
# vim: noexpandtab ts=2 sw=2 sts=2

import pylab as p
import time
import zlib

import sys, os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import config

COLORS=[]

for r in [0x00, 0x55, 0xaa]:
	for g in [0x00, 0x55, 0xaa]:
		for b in [0x00, 0x55, 0xaa]:
			c = (r << 16) + (g << 8) + b
			cs = '#{:06x}'.format(c)
			COLORS.append(cs)

def plot(timestamp, ydata, ylabel, title, color, output_file):
	f = p.figure(figsize=(4.5, 3))

	p.step(timestamp, ydata, 'r', linewidth=2, color=color)

	p.axis('tight')

	p.ylabel(ylabel)
	p.xlabel('Zeit')
	p.title(title)
	p.grid()

	# adjust xticks
	if len(timestamp) >= 2:
		r = max(timestamp) - min(timestamp)
		if r > 30*86400:
			tickdist = 30*86400
		elif r > 7*86400:
			tickdist = 7*86400
		elif r > 86400:
			tickdist = 86400
		elif r > 12*3600:
			tickdist = 6*3600
		elif r > 4*3600:
			tickdist = 3*3600
		else:
			tickdist = 3600

		start = p.floor(min(timestamp)/tickdist)*tickdist
		ticks = p.arange(start, max(timestamp), tickdist)
	else:
		ticks = p.xticks()[0]
		ticks = ticks[0:len(ticks):3]
	textticks = [time.strftime('%m-%d\n%H:%M', time.gmtime(t)) for t in ticks]

	p.xticks(ticks, textticks)
	f.savefig(output_file)

# load node names
nodenames = {}
with open(config.LOG_NODENAMES, 'r') as nodefile:
	for line in nodefile:
		nid, name = line.split(' ', 1)
		nodenames[nid] = name.strip()

# global nodes
timestamp = []
nodes = []
with open(config.LOG_NODECOUNT, 'r') as logfile:
	for line in logfile:
		data = line.strip().split(' ')

		timestamp.append(int(data[0]))
		nodes.append(int(data[1]))

	plot(timestamp,
	     nodes,
	     'Knoten',
	     'Knoten im Netzwerk',
	     COLORS[0],
	     os.path.join(config.PLOT_DIR, 'nodes.svg'))

# global online nodes
timestamp = []
nodes = []
with open(config.LOG_ONLINENODECOUNT, 'r') as logfile:
	for line in logfile:
		data = line.strip().split(' ')

		timestamp.append(int(data[0]))
		nodes.append(int(data[1]))

	plot(timestamp,
	     nodes,
	     'Knoten',
	     'Knoten online',
	     COLORS[0],
	     os.path.join(config.PLOT_DIR, 'nodes_online.svg'))

# global clients
timestamp = []
clients = []
with open(config.LOG_TOTALCLIENTCOUNT, 'r') as logfile:
	for line in logfile:
		data = line.strip().split(' ')

		timestamp.append(int(data[0]))
		clients.append(int(data[1]))

	plot(timestamp,
	     clients,
	     'Clients',
	     'Clients im Netz',
	     COLORS[0],
	     os.path.join(config.PLOT_DIR, 'clients.svg'))

# clients for each node
clientdata = {}

with open(config.LOG_NODECLIENTCOUNT, 'r') as logfile:
	for line in logfile:
		data = line.strip().split(' ')

		timestamp = int(data[0])
		nid = data[1]
		clients = int(data[2])

		if nid not in clientdata.keys():
			clientdata[nid] = {'timestamp': [], 'clients': []}

		clientdata[nid]['timestamp'].append(timestamp)
		clientdata[nid]['clients'].append(clients)

	for nid, data in clientdata.items():
		if nid in nodenames.keys():
			name = nodenames[nid]
		else:
			name = '[' + nid + ']'

		color = COLORS[zlib.crc32(bytes(nid, 'ascii')) % len(COLORS)]

		plot(data['timestamp'],
		     data['clients'],
		     'Clients',
		     'Clients an Knoten {}'.format(name),
		     color,
		     os.path.join(config.PLOT_DIR, 'clients_{}.svg'.format(nid)))
