#!/usr/bin/env python3
# vim: noexpandtab ts=2 sw=2 sts=2

import sys, os
import time

from glob import glob

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import config

def node_plot_exists(nid):
	return os.path.exists(os.path.join(config.PLOT_DIR, 'clients_{:s}_3h.svg'.format(nid)))

def mkplotline(title, html_id, basepath):
	return """
		<div id="{1:s}" class="history_box">
			<h2>{0:s}</h2>
			<p class="plot_line">
				   <span class="plot 1year"><img src="{2:s}_1year.svg"></span><!--
				--><span class="plot 30d"><img src="{2:s}_30d.svg"></span><!--
				--><span class="plot 24h"><img src="{2:s}_24h.svg"></span><!--
				--><span class="plot 3h"><img src="{2:s}_3h.svg"></span>
			</p>
		</div>
		""".format(title, html_id, basepath)

# load node names
nodenames = {}
with open(config.LOG_NODENAMES, 'r') as nodefile:
	for line in nodefile:
		nid, name = line.split(' ', 1)
		nodenames[name.strip()] = nid.strip()

htmlstring = ""

pathprefix = os.path.relpath(config.PLOT_DIR, os.path.dirname(config.PLOT_HTML))

# export pathprefix to the javascript
htmlstring += '<script type="text/javascript">pathprefix = "{:s}";</script>'.format(pathprefix)

htmlstring += mkplotline("Bekannte Knoten", 'nodes', os.path.join(pathprefix, 'nodes'))
htmlstring += mkplotline("Knoten online", 'nodes_online', os.path.join(pathprefix, 'nodes_online'))
htmlstring += mkplotline("Clients verbunden", 'clients', os.path.join(pathprefix, 'clients'))

names = list(nodenames.keys())
names.sort(key=str.lower)

# generate jump list
htmlstring += '<div class="jumplist"><h2>Knotenliste</h2><p>'
for name in names:
	nid = nodenames[name]
	if node_plot_exists(nid):
		htmlstring += '<span class="jumpentry"><a href="javascript:update_plots(\'{0:s}\', \'{1:s}\')">{1:s}</a></span> '.format(
				nodenames[name],
				name)
htmlstring += '</p></div>'

# generate node plot lines
for idx in range(len(names)):
	name = names[idx]
	nid = nodenames[name]

	if node_plot_exists(nid):
		htmlstring += mkplotline(
				"Clients an {}".format(name),
				'node_clients',
				os.path.join(pathprefix, 'clients_{}'.format(nid)))
		break;

htmlstring += '<p class="date">Letzte Aktualisierung: {:s}</p>'.format(
		time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))

with open('plot/template.html', 'r') as templatefile:
	templatecontent = templatefile.read()

	output_html = templatecontent.replace('{CONTENT}', htmlstring)

with open(config.PLOT_HTML, 'w') as outputfile:
	outputfile.write(output_html)
