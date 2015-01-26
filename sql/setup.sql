CREATE TABLE node_highscores (id TEXT PRIMARY KEY, clients INTEGER, timestamp INTEGER);

CREATE TABLE highscores (key TEXT PRIMARY KEY, value INTEGER, timestamp INTEGER);

INSERT INTO highscores VALUES
	('nodes', 0, 0),
	('nodes_online', 0, 0),
	('clients', 0, 0);
