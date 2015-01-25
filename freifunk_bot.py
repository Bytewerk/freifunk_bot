#!/usr/bin/env python3
# vim: noexpandtab ts=2 sw=2 sts=2

import irc.client
import requests
import time
import sys
import os
import threading
import sqlite3

import config

class Node:
	def __init__(self, json_obj):
		self.nid = json_obj['id']
		self.name = json_obj['name']
		self.online = json_obj['flags']['online']
		self.clients = json_obj['clientcount']
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

class FreifunkBot(irc.client.SimpleIRCClient):
	def __init__(self, target):
		irc.client.SimpleIRCClient.__init__(self)
		self.target = target

		# map of id => node data
		self.known_nodes = {}
		self.num_clients = 0

		self.timer = threading.Thread(target=self.scheduler, daemon=True);

		self.known_nodes_lock = threading.Lock()

	def on_welcome(self, connection, event):
		if irc.client.is_channel(self.target):
			connection.join(self.target)
		elif not self.timer.is_alive():
			self.timer.start()

	def on_join(self, connection, event):
		if not self.timer.is_alive():
			self.timer.start()

	def on_disconnect(self, connection, event):
		self.timer.stop()
		sys.exit(0)

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
					num_nodes = len(self.known_nodes)
					self.send_command_response("Das Netzwerk besteht zur Zeit aus {} Knoten mit {} Clients.".format(num_nodes, self.num_clients), response_target)
			else:
				with self.known_nodes_lock:
					node = self.find_node(cmdparts[1])
					if node:
						if node.online:
							self.send_command_response("Knoten {} [{}] ist online und hat {} Clients.".format(node.name, node.nid, node.clients), response_target)
						else:
							self.send_command_response("Knoten {} [{}] ist offline.".format(node.name, node.nid, node.clients), response_target)
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

		elif command == "help":
			self.send_command_response("status [<node>]   Status des Netzwerks oder eines Knotens anzeigen", response_target)
			self.send_command_response("nodes [<cols>]    Alle Knoten im Netz auflisten (ID und Name), in <cols> Spalten", response_target)
			self.send_command_response("<node> kann ein Knoten-Name oder eine ID (MAC-Adresse) sein.", response_target)
		else:
			self.send_command_response("Unbekannter Befehl. Benutze !help, um Befehle aufzulisten.", response_target)

	def scheduler(self):
		while True:
			self.do_freifunk_cycle()
			time.sleep(config.UPDATE_INTERVAL)

	def do_freifunk_cycle(self):
		try:
			r = requests.get(config.JSON_URI)
		except:
			print("Request failed")
			return

		with self.known_nodes_lock:
			json = r.json()

			current_nodes = {}
			for node in json['nodes']:
				n = Node(node)

				current_nodes[n.nid] = n

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
			for nid, node in current_nodes.items():
				if nid in self.known_nodes.keys():
					if self.known_nodes[nid].online != current_nodes[nid].online:
						changed_nodes.append(nid)

			for nid in new_nodes:
				msg = "Neuer Knoten: {:s}".format(current_nodes[nid].name)
				self.connection.notice(self.target, msg)

			for nid in really_gone_nodes:
				msg = "Knoten gelöscht: {:s}".format(self.known_nodes[nid].name)
				self.connection.notice(self.target, msg)

			for nid in changed_nodes:
				msg = "{:s} ist jetzt {}".format(
						current_nodes[nid].name,
						"online" if current_nodes[nid].online else "offline")
				self.connection.notice(self.target, msg)

			# determine nodes with new client highscores
			db = sqlite3.connect(config.DATABASE)

			for node in current_nodes.values():
				if node.updateHighscore(db) and not firstRun:
					msg = "Knoten {:s} hat neuen Client-Highscore: {:d}!".format(node.name, node.max_clients)
					self.connection.notice(self.target, msg)

			db.commit()
			db.close()

			# update current global client count
			self.num_clients = 0
			for node in current_nodes.values():
				self.num_clients += node.clients

			self.known_nodes = current_nodes


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
