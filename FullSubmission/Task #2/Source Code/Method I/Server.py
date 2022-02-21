import TL.ApplicationLayer as AL
import socket

out_filename = "out.txt"

ofile = open(out_filename, 'wb')

# Creates UDP socket object.
receive_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Defining the desired port to listen to on the server.
server_IP = '192.168.1.3'
server_port = 5000
server_address = (server_IP, server_port)

# Defining the port on the client to send ACKs to.
client_IP = '192.168.1.3'
client_port = 10000
client_address = (client_IP, client_port)

receive_socket.bind(server_address) # Server socket up for receiving data.

print("Server is listening")

#ftpserver = AL.App_Interface()
ftpserver = AL.TCPML()
buffer = ftpserver.send_ack(receive_socket, client_address)

print(len(buffer))

ordered_seq = sorted(buffer.keys())
for seq in ordered_seq:
    ofile.write(buffer[seq])
    
#print(len(buffer))