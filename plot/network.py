#!/usr/bin/env python3
# vim: noexpandtab ts=2 sw=2 sts=2

import pylab as p
import time

import sys, os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import config

def plot(timestamp, ydata, ylabel, title, output_file):
	f = p.figure()

	p.step(timestamp, ydata, 'r', linewidth=2)

	p.axis('tight')

	p.ylabel(ylabel)
	p.xlabel('Zeit')
	p.title(title)

	# adjust xticks
	ticks = p.xticks()[0]
	ticks = ticks[0:len(ticks):2]
	textticks = [time.strftime('%Y-%m-%d\n%H:%M', time.gmtime(t)) for t in ticks]

	p.xticks(ticks, textticks)
	f.savefig(output_file)


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
	     '/tmp/nodes.svg')

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
	     '/tmp/nodes_online.svg')

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
	     '/tmp/clients.svg')

# clients for each node
clientdata = {}

with open(config.LOG_NODECLIENTCOUNT, 'r') as logfile:
	for line in logfile:
		data = line.strip().split(' ')

		timestamp = int(data[0])
		name = data[1]
		clients = int(data[2])

		if name not in clientdata.keys():
			clientdata[name] = {'timestamp': [], 'clients': []}

		clientdata[name]['timestamp'].append(timestamp)
		clientdata[name]['clients'].append(clients)

	for name, data in clientdata.items():
		plot(data['timestamp'],
				 data['clients'],
				 'Clients',
				 'Clients an Knoten {}'.format(name),
				 '/tmp/clients_{}.svg'.format(name))
