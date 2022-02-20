import socket
import sys

out_filename = r"D:\Home\Computer Science\Computer Networks\out"

ofile = open(out_filename, "wb")

MSS = 4096
S_PORT = 5051
S_IP = "192.168.0.5"
ADDR = (S_IP, S_PORT)
FORMAT = 'utf-8'

server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server.bind((S_IP,S_PORT))

R_IP = '192.168.0.5'
R_PORT = 10001

clt_send_addr = (R_IP,R_PORT)

print ("Server is listening!!!!")

FIN = 0
expected_seqnum = 0
buffer = {}


while FIN!=1:
    # send a thank you message to the client. encoding to send byte type.
    ack = server.recvfrom(MSS)
    rec_mes = ack[0].split(b';', 3) 
    SYN = rec_mes[0]
    SYN = int(SYN)
    FIN = rec_mes[1]
    FIN = int(FIN)
    seqnum = rec_mes[2]
    seqnum = int(seqnum)
    if FIN == 0 and SYN == 0:
        
        buffer[seqnum] = b""
        buffer[seqnum] = buffer[seqnum].join(rec_mes[3:])
        send_syn = (str(0)+";").encode('utf-8')
        send_fin = (str(0)+";").encode('utf-8')
        send_seqnum = str(seqnum).encode('utf-8')
        send_ack = send_syn+send_fin+send_seqnum
        server.sendto(send_ack, clt_send_addr)

    else:
        print(ack[0])
        server.sendto(ack[0],clt_send_addr)

ordered_seq = sorted(buffer.keys())
#print(ordered_seq)
#data = b""
for seq in ordered_seq:
    #if seq%1000 == 0:
    #    print(seq)
    #data += buffer[seq]
    ofile.write(buffer[seq])

#print("I am here!!")
#ofile.write(data)
print("server is sleeping")
server.close()
ofile.close()

