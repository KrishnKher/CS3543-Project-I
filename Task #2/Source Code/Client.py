import TL.ApplicationLayer as AL
import socket


input_filename = r"CS3543_100MB"

# Creates UDP socket objects.
send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
receive_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Defining the desired port to connect to on the server.
server_IP = '192.168.1.3'
server_port = 5000
server_address = (server_IP, server_port)

# Defining the port on which the client receives ACKs.
client_IP = '192.168.1.3'
client_port = 10000
client_address = (client_IP, client_port)

send_socket.connect(server_address) # Client connects to the server.
receive_socket.bind(client_address) # Client socket up for receiving ACKs.

ftpclient = AL.App_Interface()
ftpclient.sendSYN(send_socket, receive_socket, server_address)
ftpclient.send(send_socket, input_filename, server_address, receive_socket)
ftpclient.close_conn(send_socket, receive_socket, server_address)

'''
any flags to be handled here
'''
