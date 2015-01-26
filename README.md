# Freifunk-Bot

Ein IRC-Bot für Freifunk-Netze, geschrieben in Python 3.

## Aktueller Stand

Die nodes.json einer Freifunk-Community wird regelmäßig abgefragt und Änderungen werden im Channel angezeigt. Dazu gehören:

- Neue Knoten
- Gelöschte Knoten
- Änderungen im online/offline-Status

Weitere Features:

- Highscore-Tracking:
	- Anzahl an Knoten im Netz
	- Anzahl der Knoten, die gerade online sind
	- Gesamtanzahl der Clients im Netz
	- Anzahl der Clients für jeden Knoten
- Interaktivität, d.h. Befehle für:
	- Status-Abfrage
	- Highscore-Abfrage
	- Auflistung aller Knoten (nur als private Nachricht)
	- Aktualisierung des Channel-Themas (Alles nach dem letzten "|" wird durch den Bot ersetzt)

## Abhängigkeiten

Python-Module:

- irc ( https://pypi.python.org/pypi/irc )
- requests ( https://pypi.python.org/pypi/requests/2.5.1 )
