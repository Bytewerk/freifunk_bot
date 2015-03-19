#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <ctype.h>
#include <errno.h>
#include <time.h>

#include <signal.h>

#include <arpa/inet.h>
#include <ifaddrs.h>
#include <netdb.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>

#include "logger.h"

#define MAX_CLIENTS 64
#define RDATA_LEN 1024

#define max(a, b) ((a > b) ? a : b)

int running = 1;
short port = 1234;

// signal handler for SIGTERM, SIGINT, etc.
// sets the flag for a clean shutdown
void sig_shutdown_handler(int sig) {
	LOG(LVL_DEBUG, "Handling signal: %i", sig);
	running = 0;
}

void init_signal_handlers(void) {
	struct sigaction sa;
	sa.sa_handler = sig_shutdown_handler;
	sigemptyset(&sa.sa_mask);
	sa.sa_flags = 0;
	sa.sa_restorer = NULL;

	if(sigaction(SIGTERM, &sa, NULL) == -1) {
		LOG(LVL_ERR, "sigaction [SIGTERM] failed: %s", strerror(errno));
	}

	if(sigaction(SIGINT, &sa, NULL) == -1) {
		LOG(LVL_ERR, "sigaction [SIGINT] failed: %s", strerror(errno));
	}

	sa.sa_handler = SIG_IGN;

	if(sigaction(SIGPIPE, &sa, NULL) == -1) {
		LOG(LVL_ERR, "sigaction [SIGPIPE] failed: %s", strerror(errno));
	}
}

int listen_socket(int listen_port)
{
	struct sockaddr_in a;
	int s;

	if ((s = socket(AF_INET, SOCK_STREAM, 0)) == -1) {
		LOG(LVL_DEBUG, "socket failed: %d = %s", errno, strerror(errno));
		return -1;
	}
	memset(&a, 0, sizeof(a));
	a.sin_port = htons(listen_port);
	a.sin_family = AF_INET;
	if (bind(s, (struct sockaddr *) &a, sizeof(a)) == -1) {
		LOG(LVL_DEBUG, "bind failed: %d = %s", errno, strerror(errno));
		close(s);
		return -1;
	}
	LOG(LVL_DEBUG, "accepting connections on port %d", listen_port);
	listen(s, 10);
	return s;
}

void shutdown_client(int *fdp) {
	shutdown(*fdp, SHUT_RDWR);
	close(*fdp);
	*fdp = -1;
}

int accept_new_clients(int ls, int *clients) {

	return 1;
}

int send_message(int *clients, char *message) {

	return 1;
}

void fsleep(float t) {
	struct timespec ts;
	ts.tv_sec = (int)t;
	ts.tv_nsec = (t - (int)t) * 1e9;

	nanosleep(&ts, NULL);
}

int main(void)
{
	int ls = -1;
	int i;
	int input_fd = -1;
	int clients[MAX_CLIENTS];
	fd_set rd;
	fd_set wr;
	int r;
	char buf[128];
	char rdata[RDATA_LEN];
	int rdata_cur_len = 0;
	int nfds = 0;


	logger_init();
	init_signal_handlers();

	ls = listen_socket(port);
	if(ls == -1) {
		return EXIT_FAILURE;
	}

	for(i = 0; i < MAX_CLIENTS; i++) {
		clients[i] = -1;
	}

	while(running) {
		// reopen the FIFO if it is closed. FIFOs are blocking if there is no writer.
		if(input_fd == -1) {
			input_fd = open("distserv.fifo", 0);
			if(input_fd == -1) {
				LOG(LVL_ERR, "Cannot open input FIFO for reading: %i = %s!", errno, strerror(errno));
				return EXIT_FAILURE;
			}
		}

		FD_ZERO(&wr);
		FD_ZERO(&rd);

		// add server socket
		FD_SET(ls, &rd);

		// add input fd
		FD_SET(input_fd, &rd);

		// add client sockets
		nfds = max(ls, input_fd);
		for(i = 0; i < MAX_CLIENTS; i++) {
			int s = clients[i];

			if(s != -1) {
				nfds = max(nfds, s);
				FD_SET(s, &rd);
			}
		}

		r = select(nfds + 1, &rd, NULL, NULL, NULL);

		// check select result for errors
		if(r == -1) {
			if(errno == EINTR) {
				continue;
			} else {
				LOG(LVL_ERR, "select failed for read list: %d = %s", errno, strerror(errno));
				break;
			}
		}

		// check wether there are new clients
		if(FD_ISSET(ls, &rd)) {
			// find a free fd
			for(i = 0; i < MAX_CLIENTS; i++) {
				if(clients[i] == -1) {
					break;
				}
			}

			if(i < MAX_CLIENTS) {
				// a free slot was found
				r = accept(ls, NULL, NULL);

				if(r == -1) {
					LOG(LVL_ERR, "accept failed: %d = %s", errno, strerror(errno));
					continue;
				} else {
					LOG(LVL_DEBUG, "new client #%i (fd=%i) accepted", i, r);
					clients[i] = r;
				}

				// a client was added, and there might be more, so try again
				continue;
			}
		}

		// check wether there is new data on the input fd
		if(FD_ISSET(input_fd, &rd)) {
			r = read(input_fd, rdata, RDATA_LEN);

			if(r == -1) {
				// read error
				LOG(LVL_ERR, "input_fd read failed (r=%i, %i = %s)", r, errno, strerror(errno));
				break;
			} else if(r == 0) {
				// nothing read, must be end of input
				LOG(LVL_INFO, "input_fd EOF");
				close(input_fd);
				input_fd = -1;
				continue;
			} else {
				rdata_cur_len = r;
			}
		}

		// check input (and EOF) for all clients
		for(i = 0; i < MAX_CLIENTS; i++) {
			int *s = clients + i;

			if(*s != -1 && FD_ISSET(*s, &rd)) {
				r = recv(*s, buf, 128, 0);
				if(r == 0) {
					LOG(LVL_DEBUG, "client #%i (fd=%i) disconnected", i, *s);
					shutdown_client(s);
					continue;
				} else if(r == -1) {
					LOG(LVL_WARN, "client #%i (fd=%i) recv failed (%i = %s)", i, *s, errno, strerror(errno));
					shutdown_client(s);
					continue;
				}
			}
		}


		// check for I/O on all clients
		if(rdata_cur_len > 0) {
			nfds = 0;
			for(i = 0; i < MAX_CLIENTS; i++) {
				int s = clients[i];

				if(s != -1) {
					nfds = max(nfds, s);
					FD_SET(s, &wr);
				}
			}

			if(nfds == 0) {
				continue; // main loop
			}

			r = select(nfds + 1, NULL, &wr, NULL, NULL);

			// check select result for errors
			if(r == -1) {
				if(errno == EINTR) {
					continue;
				} else {
					LOG(LVL_ERR, "select failed for write list: %d = %s", errno, strerror(errno));
					break;
				}
			}

			for(i = 0; i < MAX_CLIENTS; i++) {
				int *s = clients + i;

				if(*s != -1 && FD_ISSET(*s, &rd)) {
					r = recv(*s, buf, 128, 0);
					if(r == 0) {
						LOG(LVL_DEBUG, "client #%i (fd=%i) disconnected", i, *s);
						shutdown_client(s);
						continue;
					} else if(r == -1) {
						LOG(LVL_WARN, "client #%i (fd=%i) recv failed (%i = %s)", i, *s, errno, strerror(errno));
						shutdown_client(s);
						continue;
					}
				}

				if(*s != -1 && FD_ISSET(*s, &wr)) {
					r = send(*s, rdata, rdata_cur_len, 0);
					if(r < 1) {
						LOG(LVL_WARN, "client #%i (fd=%i) dropped on write (r=%i)", i, *s, r);
						shutdown_client(s);
					}
				}
			}

			// data was processed
			rdata_cur_len = 0;
		}
	}

	LOG(LVL_INFO, "Closing all the sockets.");

	for(i = 0; i < MAX_CLIENTS; i++) {
		if(clients[i] != -1) {
			shutdown_client(clients + i);
		}
	}

	close(ls);
	close(input_fd);
}
