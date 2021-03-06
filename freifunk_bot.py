#!/usr/bin/env python3
# vim: noexpandtab ts=2 sw=2 sts=2

import irc.client
import requests
import time
import sys
import os
import threading
import sqlite3
import json

import config

class Ratelimiter:
	def __init__(self):
		self.ratelimitMessages = 0
		self.nextMessageTime = 0

	def ratelimit(self):
		now = time.time()

		if now < self.nextMessageTime:
			# bot is sending too fast
			self.ratelimitMessages += 1

			print("RATELIMITER: {} messages too fast.".format(self.ratelimitMessages))

			if self.ratelimitMessages > config.RATELIMIT_MESSAGES:
				time.sleep(self.nextMessageTime - now)
		else:
			self.ratelimitMessages = 0

		self.nextMessageTime = time.time() + config.RATELIMIT_INTERVAL

class EventHandler:
	def __init__(self):
		self.broadcastFIFO = open(config.DISTSERV_FIFO, 'w')
		self.fifoOpen = True
		self.timestamp = time.time()

		self.sendBroadcast({'info': 'Startup successful'})

	def setConnection(self, conn):
		self.connection = conn

	def setTarget(self, target):
		self.target = target

	def setRatelimiter(self, rl):
		self.ratelimiter = rl

	def setTimestamp(self, ts):
		self.timestamp = ts

	def sendBroadcast(self, eventDict):
		# add a timestamp to all messages
		eventDict['timestamp'] = self.timestamp

		try:
			if not self.fifoOpen:
				# try to reopen the FIFO
				self.broadcastFIFO = open(config.DISTSERV_FIFO, 'w')
				self.fifoOpen = True

			self.broadcastFIFO.write(json.dumps(eventDict) + "\n")
			self.broadcastFIFO.flush()
		except BrokenPipeError:
			self.fifoOpen = False

	def sendNotice(self, message):
		self.ratelimiter.ratelimit()
		self.connection.notice(self.target, message)

	# Notifications about Highscores
	def highscoreRegisteredNodes(self, count):
		eventDict = {'type': 'registered_nodes', 'highscore': True, 'count': count}
		self.sendBroadcast(eventDict)

		if config.NOTIFY_NET_HIGHSCORES:
			self.sendNotice("Neuer Highscore: {:d} registrierte Knoten!".format(count))

	def highscoreOnlineNodes(self, count):
		eventDict = {'type': 'online_nodes', 'highscore': True, 'count': count}
		self.sendBroadcast(eventDict)

		if config.NOTIFY_NET_HIGHSCORES:
			self.sendNotice("Neuer Highscore: {:d} Knoten online!".format(count))

	def highscoreOnlineClients(self, count):
		eventDict = {'type': 'clients', 'highscore': True, 'count': count}
		self.sendBroadcast(eventDict)

		if config.NOTIFY_NODE_HIGHSCORES:
			self.sendNotice("Neuer Highscore: {:d} Clients verbunden!".format(count))

	def highscoreClientsAtNode(self, node):
		eventDict = {'type': 'node_clients', 'highscore': True, 'node': node.toDict()}
		self.sendBroadcast(eventDict)

		if config.NOTIFY_NODE_CLIENT_HIGHSCORES:
			self.sendNotice("Neuer Highscore: Knoten {:s} hat {:d} Clients!".format(node.readableName(), node.max_clients))

	# Notifications about Network Changes
	def newNode(self, node):
		eventDict = {'type': 'new_node', 'node': node.toDict()}
		self.sendBroadcast(eventDict)

		if config.NOTIFY_NEW_NODES:
			self.sendNotice("Neuer Knoten: {:s}".format(node.readableName()))

	def nodeDeleted(self, node):
		eventDict = {'type': 'node_deleted', 'node': node.toDict()}
		self.sendBroadcast(eventDict)

		if config.NOTIFY_DELETED_NODES:
			self.sendNotice("Knoten gelöscht: {:s}".format(node.readableName()))

	def nodeRenamed(self, node, old_node):
		eventDict = {'type': 'node_renamed', 'node': node.toDict(), 'node_name_prev': old_node.name}
		self.sendBroadcast(eventDict)

		if config.NOTIFY_RENAMED_NODES:
			self.sendNotice("Knoten {:s} heißt jetzt {:s}".format(old_node.readableName(), node.readableName()))

	def nodeStatusChanged(self, node):
		eventDict = {'type': 'online_status_changed', 'node': node.toDict()}
		self.sendBroadcast(eventDict)

		if config.NOTIFY_ONLINE_STATUS:
			self.sendNotice("{:s} ist jetzt {}".format(
				node.readableName(),
				"online" if node.online else "offline"))

	def registeredNodesChanged(self, count):
		eventDict = {'type': 'registered_nodes', 'highscore': False, 'count': count}
		self.sendBroadcast(eventDict)

	def onlineNodesChanged(self, count):
		eventDict = {'type': 'online_nodes', 'highscore': False, 'count': count}
		self.sendBroadcast(eventDict)

	def clientsChanged(self, count):
		eventDict = {'type': 'clients', 'highscore': False, 'count': count}
		self.sendBroadcast(eventDict)

	def clientsAtNodeChanged(self, node):
		eventDict = {'type': 'node_clients', 'highscore': False, 'node': node.toDict()}
		self.sendBroadcast(eventDict)


class Node:
	def __init__(self, json_obj):
		self.nid = json_obj['nodeinfo']['network']['mac']
		self.name = json_obj['nodeinfo']['hostname']
		self.online = json_obj['flags']['online']
		self.clients = json_obj['statistics']['clients']
		self.max_clients = -1
		self.max_clients_timestamp = -1
		self.delete_counter = 0

	def loadMaxClients(self, db):
		c = db.cursor()

		c.execute('SELECT clients, timestamp FROM node_highscores WHERE id=?', (self.nid,) )

		row = c.fetchone()

		if row:
			self.max_clients, self.max_clients_timestamp = row

	def saveMaxClients(self, db):
		c = db.cursor()
		result = c.execute('INSERT OR REPLACE INTO node_highscores VALUES(?, ?, ?)', (self.nid, self.max_clients, self.max_clients_timestamp) )

	# returns True if a new highscore is reached, False otherwise
	def updateHighscore(self, db):
		if self.max_clients == -1:
			self.loadMaxClients(db)

		if self.clients > self.max_clients:
			# new highscore!
			self.max_clients = self.clients
			self.max_clients_timestamp = int(time.time())
			self.saveMaxClients(db)
			return True
		else:
			return False

	def readableName(self):
		if self.name:
			return self.name
		else:
			return "[" + self.nid + "]"

	def fullIdentifier(self):
		return "{} [{}]".format(self.name, self.nid)

	def toDict(self):
		return {'id': self.nid,
		        'name': self.name,
		        'online': self.online,
		        'clients': self.clients}

class Highscore:
	def __init__(self, key):
		self.key       = key
		self.value     = 0
		self.timestamp = 0

	def update(self, value):
		if value > self.value:
			self.value = value
			self.timestamp = int(time.time())
			return True
		else:
			return False

	def load(self, db):
		c = db.cursor();
		result = c.execute('SELECT value, timestamp FROM highscores WHERE key=?', (self.key,) )

		row = c.fetchone()

		if row:
			self.value, self.timestamp = row

	def save(self, db):
		c = db.cursor();
		c.execute('UPDATE highscores SET value=?, timestamp=? WHERE key=?', (self.value, self.timestamp, self.key) )

class FreifunkBot(irc.client.SimpleIRCClient):
	def __init__(self, target):
		irc.client.SimpleIRCClient.__init__(self)
		self.target = target

		# map of id => node data
		self.known_nodes      = {}
		self.num_clients      = 0
		self.num_nodes        = 0
		self.num_nodes_online = 0

		self.last_nodes_online = 0

		self.channel_topic = ""

		self.ratelimiter = Ratelimiter()

		self.eventHandler = EventHandler()
		self.eventHandler.setTarget(target)
		self.eventHandler.setRatelimiter(self.ratelimiter)

		self.nodes_highscore        = Highscore('nodes')
		self.clients_highscore      = Highscore('clients')
		self.nodes_online_highscore = Highscore('nodes_online')

		# load the global highscores
		db = sqlite3.connect(config.DATABASE)

		self.nodes_highscore.load(db)
		self.clients_highscore.load(db)
		self.nodes_online_highscore.load(db)

		db.close()

		self.timer = threading.Thread(target=self.scheduler, daemon=True);

		self.known_nodes_lock = threading.Lock()

	def on_welcome(self, connection, event):
		# send authentication message
		if config.AUTH_MESSAGE:
			connection.privmsg(config.AUTH_TARGET, config.AUTH_MESSAGE)

		if irc.client.is_channel(self.target):
			connection.join(self.target)
		elif not self.timer.is_alive():
			self.timer.start()

	def on_join(self, connection, event):
		if not self.timer.is_alive():
			self.timer.start()

	def on_disconnect(self, connection, event):
		print("DISCONNECTED! Starting reconnect timer")
		threading.Timer(config.RECONNECT_INTERVAL, connection.reconnect).start()

	def on_currenttopic(self, connection, event):
		print("CURRENTTOPIC {}: {}".format(event.source, event.arguments))
		self.channel_topic = event.arguments[1]

	def on_topic(self, connection, event):
		print("TOPIC {}: {}".format(event.source, event.arguments[0]))
		self.channel_topic = event.arguments[0]

	def on_privmsg(self, connection, event):
		source = event.source.split('!',1)[0]
		msg = event.arguments[0]
		print("PRIVMSG {}: {}".format(source, msg))

		self.handle_message(msg, source, False)

	def on_pubmsg(self, connection, event):
		source = self.target
		msg = event.arguments[0]
		print("PUBMSG {}: {}".format(source, msg))

		self.handle_message(msg, source, True)

	def send_command_response(self, message, target):
		self.ratelimiter.ratelimit()
		self.connection.privmsg(target, message)

	def find_node(self, identifier):
		for node in self.known_nodes.values():
			if node.name == identifier or node.nid == identifier:
				return node
		else:
			return None

	def handle_message(self, message, response_target, is_public):
		# check if this is a command for me
		if message[0] != '!':
			return

		cmdparts = (message[1:]).split(' ')
		print(cmdparts)

		if len(cmdparts) < 1:
			return

		command = cmdparts[0]

		if command == "status":
			if len(cmdparts) == 1:
				with self.known_nodes_lock:
					self.send_command_response(
							"Status des gesamten Netzwerks: {} von {} Knoten online mit {} Clients.".format(
								self.num_nodes_online,
								self.num_nodes,
								self.num_clients),
							response_target)
			else:
				with self.known_nodes_lock:
					node = self.find_node(cmdparts[1])
					if node:
						if node.online:
							self.send_command_response(
									"Knoten {} ist online und hat {} Clients.".format(
										node.fullIdentifier(), node.clients),
									response_target)
						else:
							self.send_command_response("Knoten {} ist offline.".format(node.fullIdentifier()), response_target)
					else:
						self.send_command_response("Es gibt keinen Knoten mit diesem Namen.", response_target)
		elif command == "highscore":
			if len(cmdparts) == 1:
				with self.known_nodes_lock:
					self.send_command_response(
							"Knoten im Netzwerk: {:4d}, erreicht: {}".format(
								self.nodes_highscore.value,
								time.strftime(config.TIME_FORMAT, time.localtime(self.nodes_highscore.timestamp))),
							response_target)
					self.send_command_response(
							"Knoten online:      {:4d}, erreicht: {}".format(
								self.nodes_online_highscore.value,
								time.strftime(config.TIME_FORMAT, time.localtime(self.nodes_online_highscore.timestamp))),
							response_target)
					self.send_command_response(
							"Clients verbunden:  {:4d}, erreicht: {}".format(
								self.clients_highscore.value,
								time.strftime(config.TIME_FORMAT, time.localtime(self.clients_highscore.timestamp))),
							response_target)
			else:
				with self.known_nodes_lock:
					node = self.find_node(cmdparts[1])
					if node:
						self.send_command_response(
								"Knoten {} hatte bisher max. {} Clients (erreicht: {}).".format(
									node.fullIdentifier(), node.max_clients,
									time.strftime(config.TIME_FORMAT, time.localtime(node.max_clients_timestamp))),
								response_target)
					else:
						self.send_command_response("Es gibt keinen Knoten mit diesem Namen.", response_target)
		elif command == "nodes":
			if is_public:
				self.send_command_response("Dieser Befehl ist nur als private Nachricht erlaubt.", response_target)
				return

			cols = 3
			if len(cmdparts) >= 2:
				try:
					cols = int(cmdparts[1])
				except ValueError:
					pass # use default

			with self.known_nodes_lock:
				max_name_len = 0
				for node in self.known_nodes.values():
					if len(node.name) > max_name_len:
						max_name_len = len(node.name)

				i = 0
				msg = ""
				for node in self.known_nodes.values():
					msg += "[{0}] {1:{width}} ".format(node.nid, node.name, width=max_name_len)
					if i % cols == (cols - 1):
						self.send_command_response(msg.rstrip(), response_target)
						msg = ""

					i += 1

				if msg != "":
					self.send_command_response(msg, response_target)

		elif command == "topic":
			pos = self.channel_topic.rfind('|')
			new_topic = "{}| {} von {} Knoten online".format(
					self.channel_topic[0:pos],
					self.num_nodes_online,
					self.num_nodes)

			if config.TOPIC_USE_CHANSERV:
				self.connection.privmsg("chanserv", "topic {} {}".format(self.target, new_topic))
			else:
				self.connection.topic(self.target, new_topic)
		elif command == "top":
			num = 3
			if len(cmdparts) >= 2:
				try:
					num = int(cmdparts[1])
				except ValueError:
					pass # use default

			num = min(num, len(self.known_nodes))

			nodes_limited = False
			if is_public and num > config.PUBLIC_MAX_NODES:
				nodes_limited = True
				num = config.PUBLIC_MAX_NODES

			with self.known_nodes_lock:
				nodes_cur_clients = []
				nodes_max_clients = []
				max_name_len = 0

				for node in self.known_nodes.values():
					nodes_cur_clients.append( (node.clients, node.nid) )
					nodes_max_clients.append( (node.max_clients, node.nid) )

					if len(node.name) > max_name_len:
						max_name_len = len(node.name)

				nodes_cur_clients.sort(reverse=True)
				nodes_max_clients.sort(reverse=True)

				# -- Clients aktuell -----------------|-- Client-Highscore ----------------
				# [00:00:00:00:00:00] Knoten-Name     |[00:00:00:00:00:00] Knoten-Name

				col_width = 25 + max_name_len + 1
				msg = '-- Clients aktuell ' + '-'*(col_width-19) + '|-- Client-Highscore ' + '-'*(col_width-20)
				self.send_command_response(msg, response_target)

				for i in range(num):
					lnode = self.known_nodes[ nodes_cur_clients[i][1] ]
					rnode = self.known_nodes[ nodes_max_clients[i][1] ]

					msg = "{0:4d} [{1}] {2:{width}} |{3:4d} [{4}] {5:{width}} ".format(
							lnode.clients, lnode.nid, lnode.name,
							rnode.max_clients, rnode.nid, rnode.name,
							width=max_name_len)
					self.send_command_response(msg, response_target)

				if nodes_limited:
					msg = 'Im Channel werden maximal {} Knoten aufgelistet. Benutze eine private Nachricht, um mehr Knoten aufzulisten.'.format(config.PUBLIC_MAX_NODES)
					self.send_command_response(msg, response_target)

		elif command == "help":
			self.send_command_response("status [<node>]     Status des Netzwerks oder eines Knotens anzeigen", response_target)
			self.send_command_response("highscore [<node>]  Highscores des Netzwerks oder eines Knotens anzeigen", response_target)
			self.send_command_response("nodes [<cols>]      Alle Knoten im Netz auflisten (ID und Name), in <cols> Spalten", response_target)
			self.send_command_response("top [<num>]         Die <num> meistgenutzen Knoten auflisten (aktuell und Highscore)", response_target)
			self.send_command_response("topic               Topic mit aktuellen Knotenzahlen aktualisieren (Text nach letztem | wird ersetzt)", response_target)
			self.send_command_response("<node> kann ein Knoten-Name oder eine ID (MAC-Adresse) sein.", response_target)
		else:
			self.send_command_response("Unbekannter Befehl. Benutze !help, um Befehle aufzulisten.", response_target)

	def scheduler(self):
		while True:
			self.do_freifunk_cycle()
			time.sleep(config.UPDATE_INTERVAL)

	def do_freifunk_cycle(self):
		try:
			r = requests.get(config.JSON_URI, timeout=config.REQUEST_TIMEOUT)
		except Exception as e:
			print("Request failed: {}".format(str(e)))
			return

		with self.known_nodes_lock:
			try:
				json = r.json()
			except ValueError as e:
				print("Failed to parse JSON:".format(str(e)))
				return

			current_nodes = {}
			for node in json['nodes'].values():
				try:
					n = Node(node)
					current_nodes[n.nid] = n
				except KeyError as e:
					# node is missing relevant information for tracking
					pass

			# Update connection reference of the event handler before sending messages
			self.eventHandler.setConnection(self.connection)
			self.eventHandler.setTimestamp(time.time())

			# check if this is the first run
			firstRun = not self.known_nodes
			if firstRun:
				# first load
				self.known_nodes = current_nodes
				msg = "ist initialisiert: {:d} bekannte Knoten".format(len(current_nodes))
				self.connection.action(self.target, msg)

			current_nids = set(current_nodes.keys())
			known_nids = set(self.known_nodes.keys())

			new_nodes  = list(current_nids - known_nids)
			gone_nodes = list(known_nids - current_nids)

			really_gone_nodes = []
			for nid in gone_nodes:
				n = self.known_nodes[nid]
				n.delete_counter += 1
				print("{} not seen for {} update cycles".format(n.name, n.delete_counter))

				if n.delete_counter >= config.DELETE_TIMEOUT:
					# if a node was gone long enough, really drop and report it
					really_gone_nodes.append(nid)
				else:
					# if not, put it back as "still here"
					current_nodes[nid] = n

			changed_nodes = []
			renamed_nodes = []
			for nid, node in current_nodes.items():
				if nid in self.known_nodes.keys():
					if self.known_nodes[nid].online != current_nodes[nid].online:
						changed_nodes.append(nid)
					if self.known_nodes[nid].name != current_nodes[nid].name:
						renamed_nodes.append(nid)

			for nid in new_nodes:
				self.eventHandler.newNode(current_nodes[nid])

			for nid in really_gone_nodes:
				self.eventHandler.nodeDeleted(self.known_nodes[nid])

			for nid in changed_nodes:
				self.eventHandler.nodeStatusChanged(current_nodes[nid])

			for nid in renamed_nodes:
				self.eventHandler.nodeRenamed(current_nodes[nid], self.known_nodes[nid])

			# update global network status
			self.last_nodes_online = self.num_nodes_online
			self.last_nodes = self.num_nodes
			self.last_clients = self.num_clients

			self.num_nodes = len(current_nodes)
			self.num_nodes_online = 0
			self.num_clients = 0
			for node in current_nodes.values():
				self.num_clients += node.clients
				if node.online:
					self.num_nodes_online += 1

			# Check new highscores
			db = sqlite3.connect(config.DATABASE)

			# per-node client highscore
			for node in current_nodes.values():
				if node.updateHighscore(db) and not firstRun and node.max_clients > 0:
					self.eventHandler.highscoreClientsAtNode(node)

			db.commit()

			# nodes registered
			if self.nodes_highscore.update(self.num_nodes):
				self.nodes_highscore.save(db)
				self.eventHandler.highscoreRegisteredNodes(self.num_nodes)

			# nodes online
			if self.nodes_online_highscore.update(self.num_nodes_online):
				self.nodes_online_highscore.save(db)
				self.eventHandler.highscoreOnlineNodes(self.num_nodes_online)

			# clients
			if self.clients_highscore.update(self.num_clients):
				self.clients_highscore.save(db)
				self.eventHandler.highscoreOnlineClients(self.num_clients)

			db.commit()
			db.close()

			# write a log of changes in the network
			self.log_network_changes(current_nodes, new_nodes, really_gone_nodes, renamed_nodes)

			self.known_nodes = current_nodes

	def log_network_changes(self, current_nodes, new_nodes, gone_nodes, renamed_nodes):
		if self.num_nodes != self.last_nodes:
			self.eventHandler.registeredNodesChanged(self.num_nodes)
			if config.LOG_NODECOUNT:
				with open(config.LOG_NODECOUNT, 'a') as logfile:
					print("Number of nodes changed: {} -> {}".format(self.last_nodes, self.num_nodes))
					logfile.write("{} {}\n".format(int(time.time()), self.num_nodes))

		if self.num_nodes_online != self.last_nodes_online:
			self.eventHandler.onlineNodesChanged(self.num_nodes_online)
			if config.LOG_ONLINENODECOUNT:
				with open(config.LOG_ONLINENODECOUNT, 'a') as logfile:
					print("Number of online nodes changed: {} -> {}".format(self.last_nodes_online, self.num_nodes_online))
					logfile.write("{} {}\n".format(int(time.time()), self.num_nodes_online))

		if self.num_clients != self.last_clients:
			self.eventHandler.clientsChanged(self.num_clients)
			if config.LOG_TOTALCLIENTCOUNT:
				with open(config.LOG_TOTALCLIENTCOUNT, 'a') as logfile:
					print("Number of connected clients changed: {} -> {}".format(self.last_clients, self.num_clients))
					logfile.write("{} {}\n".format(int(time.time()), self.num_clients))

		current_nids = set(current_nodes.keys())
		known_nids = set(self.known_nodes.keys())
		all_nids = current_nids | known_nids
		for nid in all_nids:
			clientcount = -1
			node = None
			if nid in new_nodes:
				# new node
				clientcount = current_nodes[nid].clients
				node = current_nodes[nid]
			elif nid in gone_nodes:
				# deleted node
				clientcount = 0
				node = self.known_nodes[nid]
			elif self.known_nodes[nid].clients != current_nodes[nid].clients:
				clientcount = current_nodes[nid].clients
				node = current_nodes[nid]

			if clientcount >= 0:
				self.eventHandler.clientsAtNodeChanged(node)
				if config.LOG_NODECLIENTCOUNT:
					with open(config.LOG_NODECLIENTCOUNT, 'a') as logfile:
						print("Number of clients for node {} changed: {}".format(nid, clientcount))
						logfile.write("{} {} {}\n".format(int(time.time()), nid, clientcount))

		if config.LOG_NODENAMES:
			if not os.path.exists(config.LOG_NODENAMES):
				# create the file with all current nodes
				with open(config.LOG_NODENAMES, 'w') as nodefile:
					for node in current_nodes.values():
						nodefile.write("{} {}\n".format(node.nid, node.name))
			else:
				with open(config.LOG_NODENAMES, 'a') as nodefile:
					for nid in set(new_nodes + renamed_nodes):
						node = current_nodes[nid]
						nodefile.write("{} {}\n".format(node.nid, node.name))


def main():
	if len(sys.argv) != 4:
		print("Usage: freifunk_bot.py <server[:port]> <nickname> <target>")
		print("\ntarget is a nickname or a channel.")
		sys.exit(1)

	s = sys.argv[1].split(":", 1)
	server = s[0]
	if len(s) == 2:
		try:
			port = int(s[1])
		except ValueError:
			print("Error: Erroneous port.")
			sys.exit(1)
	else:
		port = 6667
	nickname = sys.argv[2]
	target = sys.argv[3]

	c = FreifunkBot(target)
	try:
		c.connect(server, port, nickname)
	except irc.client.ServerConnectionError as x:
		print(x)
		sys.exit(1)
	c.start()

if __name__ == "__main__":
	main()
