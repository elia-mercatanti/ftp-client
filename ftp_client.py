# Author: Elia Mercatanti
# Matricola: 5619856

import os
import socket
import inspect
import string

class MyFtpClient:
    # Inizializza le strutture dati usate dal client
    def __init__(self, local_dir):
        self.working_dir = os.path.realpath(local_dir)
        self.connected = False
        self.messages_list = []
        self.connection_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.buffer_size = 1024
        self.data_socket = None
        self.pasv_mode = False
        self.passive_host = None
        self.passive_port = None
        self.port_socket = None
        self.transmission_mode = 'ASCII'

    def close_connection(self):
        self.connection_sock.close()
        self.connected = False
        self.connection_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.data_socket = None
        self.pasv_mode = False
        self.port_socket = None
        self.transmission_mode = 'ASCII'

    def send(self, cmd):
        try:
            client_message = cmd + '\r\n'
            self.messages_list.append(('c', client_message))
            self.connection_sock.sendall(client_message)
            print 'Command sent: ' + cmd
        except socket.error as e:
            print str(e)
            self.close_connection()

    def recv(self):
        try:
            server_message = self.connection_sock.recv(self.buffer_size)
            self.messages_list.append(('s', server_message))
            print 'Server response: ' + server_message
            return server_message
        except socket.error as e:
            print str(e)
            self.close_connection()

    def isconnected(self):
        return self.connected

    def lastcode(self):
        if not self.isconnected():
            return None
        elif not self.messages_list:
            raise Exception('The message log is empty.')
        else:
            for i in range(1, len(self.messages_list) + 1):
                if self.messages_list[-i][0] == 's':
                    try:
                        code = int(self.messages_list[-i][1].split()[0])
                    except ValueError:
                        code = int(self.messages_list[-i][1].split()[0][:3])
                    return code
            raise Exception('Code not found.')

    def lastmessage(self):
        for i in range(1, len(self.messages_list) + 1):
            if self.messages_list[-i][0] == 's':
                return self.messages_list[-i][1]
        raise Exception('Message not found.')

    def log(self):
        log = ''
        for message in self.messages_list:
            if message[0] == 'c':
                log = log + '>' + message[1]
            elif message[0] == 's':
                log = log + '<' + message[1]
        return log

    def connect(self, host, port):
        if self.isconnected():
            raise TypeError('The client is already connected to an FTP server.')
        else:
            try:
                self.connection_sock.connect((host, port))
                self.connected = True
                self.messages_list = []
            except socket.error as e:
                raise Exception(str(e))
            self.recv()

    def user(self, user):
        if self.isconnected():
            self.send('USER ' + user)
            self.recv()
        else:
            raise Exception('The client is not connected to an FTP server.')

    def password(self, password):
        if self.isconnected():
            self.send('PASS ' + password)
            self.recv()
        else:
            raise Exception('The client is not connected to an FTP server.')

    def system(self):
        if self.isconnected():
            self.send('SYST')
            self.recv()
        else:
            raise Exception('The client is not connected to an FTP server.')

    def disconnect(self):
        if self.isconnected():
            self.send('QUIT')
            self.recv()
            self.close_connection()
        else:
            raise Exception('The client is not connected to an FTP server.')

    def pwd(self):
        if self.isconnected():
            self.send('PWD')
            self.recv()
        else:
            raise Exception('The client is not connected to an FTP server.')

    def lpwd(self):
        return self.working_dir

    def port(self):
        if self.isconnected():
            self.port_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.port_socket.bind((self.connection_sock.getsockname()[0], 0))
            self.port_socket.listen(1)
            ip, port = self.port_socket.getsockname()
            ip = ip.split('.')
            self.send('PORT {},{},{},{},{},{}'.format(ip[0], ip[1], ip[2], ip[3], str(port // 256), str(port % 256)))
            self.recv()
            self.pasv_mode = False
        else:
            raise Exception('The client is not connected to an FTP server.')

    def get_passive_data(self, data):
        start = data.find('(')
        if start == -1:
            return None
        end = data.find(')')
        if end == -1:
            return None
        element = data[start + 1:end].split(',')
        if len(element) != 6:
            return None
        for d in element:
            if not d.isdigit():
                return None
        for i in range(0, 4):
            if not 0 <= int(i) < 255:
                return None
        if not 0 < int(element[4]) * 256 + int(element[5]) < 2 ** 16:
            return None
        return element

    def pasv(self):
        if self.isconnected():
            self.send('PASV')
            response = self.recv()
            data = self.get_passive_data(response)
            if data is not None:
                self.passive_host = string.join(data[0:4], '.')
                self.passive_port = int(data[4]) * 256 + int(data[5])
                self.pasv_mode = True
            else:
                raise Exception('The data for passive connection are wrong.')
        else:
            raise Exception('The client is not connected to an FTP server.')

    def data(self):
        if self.isconnected():
            if self.pasv_mode:
                return self.pasv_mode, self.passive_host, self.passive_port
            elif self.port_socket is not None:
                return self.pasv_mode, self.port_socket.getsockname()[0], self.port_socket.getsockname()[1]
            else:
                return None
        else:
            raise Exception('The client is not connected to an FTP server.')

    def cd(self, dir):
        if self.isconnected():
            self.send("CWD " + dir)
            self.recv()
        else:
            raise Exception('The client is not connected to an FTP server.')

    def lcd(self, dir):
        if not os.path.isabs(dir):
            dir = os.path.join(self.working_dir, dir)
            dir = os.path.realpath(dir)
        if os.path.isdir(dir):
            self.working_dir = dir
            return self.working_dir
        else:
            raise Exception('The directory passed is not a directory or does not exist.')

    def start_data_socket(self):
        if self.pasv_mode:
            self.data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.data_socket.connect((self.passive_host, self.passive_port))
        else:
            self.data_socket, addr = self.port_socket.accept()

    def stop_data_socket(self):
        self.data_socket.close()
        if not self.pasv_mode:
            self.port_socket.close()
            self.port_socket = None
        elif self.pasv_mode:
            self.pasv_mode = False

    def list(self, dir):
        if self.isconnected():
            if self.data() is None:
                raise Exception('The data connection has not been started. Use PASV or PORT command first.')
            else:
                self.send('LIST ' + dir)
                response = self.recv()
                if response.startswith('150'):
                    self.start_data_socket()
                    data = ''
                    message = self.data_socket.recv(self.buffer_size)
                    while message:
                        data = data + message
                        message = self.data_socket.recv(self.buffer_size)
                    self.stop_data_socket()
                    self.recv()
                    return data
                else:
                    raise Exception('The remote dir does not exist.')
        else:
            raise Exception('The client is not connected to an FTP server.')

    def cdup(self):
        if self.isconnected():
            self.send('CDUP')
            self.recv()
        else:
            raise Exception('The client is not connected to an FTP server.')

    def lcdup(self):
        self.working_dir = os.path.realpath(os.path.join(self.working_dir, '..'))
        return self.working_dir

    def ascii(self):
        if self.isconnected():
            self.send('TYPE A')
            self.recv()
            self.transmission_mode = 'ASCII'
        else:
            raise Exception('The client is not connected to an FTP server.')

    def binary(self):
        if self.isconnected():
            self.send('TYPE I')
            self.recv()
            self.transmission_mode = 'IMAGE'
        else:
            raise Exception('The client is not connected to an FTP server.')

    def mode(self):
        if self.isconnected():
            return self.transmission_mode
        else:
            raise Exception('The client is not connected to an FTP server.')

    def get(self, remote, local):
        if not self.isconnected():
            raise TypeError('The client is not connected to an FTP server.')
        elif self.data() is None:
            raise TypeError('The data connection has not been started. Use PASV or PORT command first.')
        else:
            self.send('RETR ' + remote)
            response = self.recv()
            if response.startswith('150'):
                if not os.path.isabs(local):
                    local = os.path.realpath(os.path.join(self.working_dir, local))
                if self.transmission_mode == 'IMAGE':
                    file_desc = open(local, 'wb')
                else:
                    file_desc = open(local, 'w')
                self.start_data_socket()
                data = self.data_socket.recv(self.buffer_size)
                while data:
                    if self.transmission_mode == 'ASCII':
                        data = data.replace('\r\n', '\n')
                    file_desc.write(data)
                    data = self.data_socket.recv(self.buffer_size)
                file_desc.close()
                self.stop_data_socket()
                self.recv()
            else:
                raise Exception('The remote file does not exist.')

    def put(self, local, remote):
        if not self.isconnected():
            raise Exception('The client is not connected to an FTP server.')
        elif self.data() is None:
            raise Exception('The data connection has not been started. Use PASV or PORT command first.')
        else:
            if not os.path.isabs(local):
                local = os.path.realpath(os.path.join(self.working_dir, local))
            if os.path.isfile(local):
                self.send('STOR ' + remote)
                response = self.recv()
                if response.startswith('150'):
                    if self.transmission_mode == 'IMAGE':
                        file_desc = open(local, 'rb')
                    else:
                        file_desc = open(local, 'r')
                    self.start_data_socket()
                    data = file_desc.read(self.buffer_size)
                    while data:
                        if self.transmission_mode == 'ASCII':
                            data = data.replace('\n', '\r\n')
                        self.data_socket.send(data)
                        data = file_desc.read(self.buffer_size)
                    file_desc.close()
                    self.stop_data_socket()
                    self.recv()
                else:
                    raise Exception('The local file does not exist.')
            else:
                raise Exception('The remote path does not exist.')
