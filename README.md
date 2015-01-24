# Freifunk-Bot

Ein IRC-Bot für Freifunk-Netze, geschrieben in Python 3.

## Aktueller Stand

Die nodes.json einer Freifunk-Community wird regelmäßig abgefragt und Änderungen werden im Channel angezeigt. Dazu gehören:

- Neue Knoten
- Gelöschte Knoten
- Änderungen im online/offline-Status

## Abhängigkeiten

Python-Module:

- irc ( https://pypi.python.org/pypi/irc )
- requests ( https://pypi.python.org/pypi/requests/2.5.1 )
