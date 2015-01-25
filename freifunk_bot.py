#!/usr/bin/env python3
# vim: noexpandtab ts=2 sw=2 sts=2

import irc.client
import requests
import time
import sys
import os
import threading

import config

class Node:
	def __init__(self, json_obj):
		self.nid = json_obj['id']
		self.name = json_obj['name']
		self.online = json_obj['flags']['online']
		self.delete_counter = 0

class FreifunkBot(irc.client.SimpleIRCClient):
	def __init__(self, target):
		irc.client.SimpleIRCClient.__init__(self)
		self.target = target

		# map of id => node data
		self.known_nodes = {}

		self.timer = threading.Thread(target=self.scheduler, daemon=True);

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
		print("PRIVMSG {}".format(event.arguments[0]))

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

		json = r.json()

		current_nodes = {}
		for node in json['nodes']:
			n = Node(node)

			current_nodes[n.nid] = n

		if not self.known_nodes:
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
