#!/usr/bin/env python3
# vim: noexpandtab ts=2 sw=2 sts=2

import pylab as p
import time
import zlib

import sys, os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import config

COLORS=[]

for r in [0x20, 0x65, 0xaa]:
	for g in [0x20, 0x65, 0xaa]:
		for b in [0x20, 0x65, 0xaa]:
			c = (r << 16) + (g << 8) + b
			cs = '#{:06x}'.format(c)
			COLORS.append(cs)

def init_plot():
	return p.figure(figsize=(4.5, 3.5))

def finalize_plot(f, timestamp, ylabel, title, output_file):
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
	textticks = [time.strftime('%y-%m-%d\n%H:%M', time.gmtime(t)) for t in ticks]

	p.xticks(ticks, textticks)
	f.savefig(output_file, transparent=True, bbox_inches='tight')

	p.close(f)

def plot(timestamp, ydata, ylabel, title, color, output_file):
	f = init_plot()

	p.step(timestamp, ydata, linewidth=2, color=color)

	finalize_plot(f, timestamp, ylabel, title, output_file)

def plot_minmax(timestamp, ydata, ylabel, binsize, title, color, output_file):
	f = init_plot()

	# sort data into bins with a width of binsize
	tsbins = p.multiply(p.floor(p.divide(timestamp, binsize)), binsize);

	bins = {}
	for i in range(len(timestamp)):
		if tsbins[i] not in bins.keys():
			bins[ tsbins[i] ] = [ ydata[i] ]
		else:
			bins[ tsbins[i] ].append(ydata[i])

	sorted_ts = sorted(tsbins)

	binsmax = {}
	for ts, data in bins.items():
		binsmax[ts] = max(data)

	binsmax_data = []
	for k in sorted_ts:
		binsmax_data.append(binsmax[k])

	binsmin = {}
	for ts, data in bins.items():
		binsmin[ts] = min(data)

	binsmin_data = []
	for k in sorted_ts:
		binsmin_data.append(binsmin[k])

	p.plot(sorted_ts, binsmax_data,
	       sorted_ts, binsmin_data,
	       linewidth=2, color=color)

	p.fill_between(sorted_ts, binsmin_data, binsmax_data, color=color, alpha=0.2)

	finalize_plot(f, sorted_ts, ylabel, title, output_file)

def limitdata(timestamp, data, maxage):
	out_timestamp = []
	out_data = []

	for i in range(len(timestamp)):
		if timestamp[i] > (time.time() - maxage):
			out_timestamp.append(timestamp[i])
			out_data.append(data[i])

	return out_timestamp, out_data

def plot_limited(timestamp, ydata, ylabel, basetitle, color, base_output_file):
	lim_timestamp, lim_data = limitdata(timestamp, ydata, 356*24*3600)
	plot_minmax(lim_timestamp,
	     lim_data,
	     ylabel,
	     24*3600,
	     '{} (1y)'.format(basetitle),
	     color,
	     os.path.join(config.PLOT_DIR, '{}_1year.svg'.format(base_output_file)))

	lim_timestamp, lim_data = limitdata(timestamp, ydata, 30*24*3600)
	plot_minmax(lim_timestamp,
	     lim_data,
	     ylabel,
	     3*3600,
	     '{} (30d)'.format(basetitle),
	     color,
	     os.path.join(config.PLOT_DIR, '{}_30d.svg'.format(base_output_file)))

	lim_timestamp, lim_data = limitdata(timestamp, ydata, 24*3600)
	plot(lim_timestamp,
	     lim_data,
	     ylabel,
	     '{} (24h)'.format(basetitle),
	     color,
	     os.path.join(config.PLOT_DIR, '{}_24h.svg'.format(base_output_file)))

	lim_timestamp, lim_data = limitdata(timestamp, ydata, 3*3600)
	plot(lim_timestamp,
	     lim_data,
	     ylabel,
	     '{} (3h)'.format(basetitle),
	     color,
	     os.path.join(config.PLOT_DIR, '{}_3h.svg'.format(base_output_file)))

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
	print("Reading data for nodes...")
	for line in logfile:
		data = line.strip().split(' ')

		timestamp.append(int(data[0]))
		nodes.append(int(data[1]))

	print("Plotting...")
	plot_limited(timestamp,
	             nodes,
	             'Knoten',
	             'Knoten im Netzwerk',
	             COLORS[0],
	             os.path.join(config.PLOT_DIR, 'nodes'))

# global online nodes
timestamp = []
nodes = []
with open(config.LOG_ONLINENODECOUNT, 'r') as logfile:
	print("Reading data for online nodes...")
	for line in logfile:
		data = line.strip().split(' ')

		timestamp.append(int(data[0]))
		nodes.append(int(data[1]))

	print("Plotting...")
	plot_limited(timestamp,
	             nodes,
	             'Knoten',
	             'Knoten online',
	             COLORS[0],
	             os.path.join(config.PLOT_DIR, 'nodes_online'))

# global clients
timestamp = []
clients = []
with open(config.LOG_TOTALCLIENTCOUNT, 'r') as logfile:
	print("Reading data for global clients...")
	for line in logfile:
		data = line.strip().split(' ')

		timestamp.append(int(data[0]))
		clients.append(int(data[1]))

	print("Plotting...")
	plot_limited(timestamp,
	             clients,
	             'Clients',
	             'Clients im Netz',
	             COLORS[0],
	             os.path.join(config.PLOT_DIR, 'clients'))

# clients for each node
clientdata = {}

with open(config.LOG_NODECLIENTCOUNT, 'r') as logfile:
	print("Reading data for node clients...")
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

		print("Plotting clients for node {} [{}]...".format(name, nid))
		plot_limited(data['timestamp'],
		             data['clients'],
		             'Clients',
		             'Clients an Knoten {}'.format(name),
		             color,
		             os.path.join(config.PLOT_DIR, 'clients_{}'.format(nid)))
