#!/usr/bin/env python2.7
import asyncore
import pam
import socket

class Client(asyncore.dispatcher_with_send):
    def __init__(self, sock):
        asyncore.dispatcher_with_send.__init__(self, sock)
        self._buf = ''

    def handle_read(self):
        data = self._buf + self.recv(1024)
        if not data:
            self.close()
            return
        reqs, data = data.rsplit('\r\n', 1)
        self._buf = data
        for req in reqs.split('\r\n'):
            try:
                user, passwd = req.split()
            except:
                self.send('bad\r\n')
            else:
                if pam.authenticate(user, passwd):
                    self.send('ok\r\n')
                else:
                    self.send('fail\r\n')

    def handle_close(self):
        self.close()

class Service(asyncore.dispatcher_with_send):
    def __init__(self, addr):
        asyncore.dispatcher_with_send.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind(addr)
        self.listen(1)

    def handle_accept(self):
        conn, _ = self.accept()
        Client(conn)

def main():
    addr = ('localhost', 8317)
    Service(addr)
    try:
        asyncore.loop()
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()
