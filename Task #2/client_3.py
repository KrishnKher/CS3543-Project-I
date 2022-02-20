import socket
import threading
import time
import sys
import os
#import hashlib

def packetseg(i_filename,MSS):
    ifile = open(i_filename, 'rb')

    seqcount = 0
    SYN = (str(0) + ";").encode('utf-8')
    FIN = (str(0) + ";").encode('utf-8')
    seqnum = (str(seqcount) + ";").encode('utf-8')
    header_size = sys.getsizeof(SYN+FIN+seqnum)
    #checksum = hashlib.md5((SYN+FIN+seqnum).encode('utf-8'))

    data = []
    byte = ifile.read(MSS-(header_size))
    while byte:
        SYN = (str(0)+";").encode('utf-8')
        FIN = (str(0)+";").encode('utf-8')
        seqnum = (str(seqcount)+";").encode('utf-8')
        data.append(SYN+FIN+seqnum+byte)
        byte = ifile.read(MSS - (header_size))
        seqcount += 1
        #print(data)
    ifile.close()
    return data

def send(data,N,r_addr):
    global ACK
    global lock
    base = 0
    nextseq = 0
    datasize = len(data)
    t = threading.Thread(target=recieve,args=(datasize,))
    t.start()
    u = {}
    while nextseq != datasize:
        #print("1 " + str(nextseq))
        while nextseq < base + N and nextseq != datasize:
            #print("2 " + str(nextseq))
            pkt = data[nextseq]
            #send packets using threads to improve speed
            lock.acquire()
            #print("3 " + str(pkt))
            s.sendto(pkt,r_addr)
            lock.release()
            ACK[nextseq] = False

            u[nextseq] = threading.Thread(target=timer,args=(pkt,r_addr,nextseq,N,RTO))
            u[nextseq].start()
            nextseq += 1
        while not ACK[base]:
            pass
        #ACK.pop(base)
        u[base].join()
        base += 1
    t.join()
    return

# def send_gbn(data,N,r_addr):
#     global ACK
#     global lock
#     global expected_ack
#     base = 0
#     nextseq = 0
#     expected_ack = base
#     datasize = len(data)
#     t = threading.Thread(target=recieve,args=(datasize,))
#     t.start()
#     u = {}
#     while nextseq < datasize:
#         #print("1 " + str(nextseq))
#         while nextseq < base + N and nextseq < datasize:
#             #print("2 " + str(nextseq))
#             pkt = data[nextseq]
#             #send packets using threads to improve speed
#             #lock.acquire()
#             #print("3 " + str(pkt))
#             ACK[nextseq] = False
#             s.sendto(pkt,r_addr)
#             #lock.release()
            

#             u[nextseq] = threading.Thread(target=timer,args=(pkt,r_addr,N,RTO))
#             u[nextseq].start()
#             nextseq += 1
#         while not ACK[base]:
#             pass
#         #ACK.pop(base)
#         u[base].join()
#         base += 1
#     t.join()
#     return

# def resend_window(data,base,N):
#     global ACK
#     global lock
#     global expected_ack
#     datasize = len(data)
#     nextseq = base
#     while nextseq < datasize:
#         #print("1 " + str(nextseq))
#         while nextseq < base + N and nextseq < datasize:
#             #print("2 " + str(nextseq))
#             pkt = data[nextseq]
#             #send packets using threads to improve speed
#             #lock.acquire()
#             #print("3 " + str(pkt))
#             ACK[nextseq] = False
#             s.sendto(pkt,r_addr)
#             #lock.release()
#             nextseq += 1
#         while not ACK[base]:
#             pass
#         #ACK.pop(base)
#         base += 1
#     return

def timer(pkt,addr,seqnum,N,RTO):
    global ACK
    global lock
    while True:
        start = time.time()
        #start = curr
        while time.time() - start < RTO:
            if ACK[seqnum]:
                return
        lock.acquire()
        s.sendto(pkt,addr)
        lock.release()

# def timer_gbn(data,pkt,addr,N,RTO):
#     global ACK
#     global lock
#     global expected_ack, check_timeout
#     while True:
#         start = time.time()
#         #start = curr
#         while time.time() - start < RTO:
#             if ACK[expected_ack]:
#                 check_timeout = 0
#                 return
#         lock.acquire()
#         #s.sendto(pkt,addr)
#         check_timeout = 1
#         base = expected_ack
#         resend_window(data,base,N)
#         lock.release()

def recieve(datasize):
    global ACK
    global lock
    FIN  = 0
    seqnum = 0
    while seqnum != datasize-1:
        pkt = r.recvfrom(MSS)
        SYN,FIN,seqnum = pkt[0].decode('utf-8').split(';')
        FIN = int(FIN)
        seqnum = int(seqnum)
        #check if the ack is within or lower than the window
        # if(seqnum < max(ACK.keys())):
        #ack_lock[seqnum].acquire()
        ACK[seqnum] = True
        #ack_lock[seqnum].release()
    return

# def recieve_gbn(datasize):
#     global ACK
#     global lock
#     global expected_ack
#     FIN  = 0
#     seqnum = 0
#     ack_rec = {}
#     while expected_ack != datasize-1:
#         pkt = r.recvfrom(MSS)
#         SYN,FIN,seqnum = pkt[0].decode('utf-8').split(';')
#         FIN = int(FIN)
#         seqnum = int(seqnum)
#         ack_rec[seqnum] = 1; 

#         if expected_ack in ack_rec:
#             ACK[expected_ack] = True
#             expected_ack += 1
#         #check if the ack is within or lower than the window
#         # if(seqnum < max(ACK.keys())):
#         #ack_lock[seqnum].acquire()
#         #ACK[seqnum] = True
#         #ack_lock[seqnum].release()
#     return

connection = False

def sendSYN(s):
    global connection
    SYN = (str(1)+";").encode('utf-8')
    FIN = (str(0)+";").encode('utf-8')
    seqnum = (str(0)).encode('utf-8')
    conn_pkt = SYN+FIN+seqnum
    t = threading.Thread(target=recvSYN,args=(r,))
    t.start()
    s.sendto(conn_pkt, r_addr)
    while not connection :
        print(conn_pkt)
        start = time.time()
        while time.time() - start < RTO:
                if connection:
                    break
        if not connection:
            s.sendto(conn_pkt,r_addr)
    print("ending sendSYN")
    return

def recvSYN(r):
    global connection
    SYN = 0
    while SYN!=1:
        pkt = r.recvfrom(MSS)
        SYN,FIN,seqnum = pkt[0].decode('utf-8').split(";")
        SYN = int(SYN)
    print("Connection established from server")
    connection = True
    return

def recvFIN(r):
    global connection
    FIN = 0
    while FIN!=1:
        pkt = r.recvfrom(MSS)
        SYN,FIN,seqnum = pkt[0].decode('utf-8').split(";")
        FIN = int(FIN)
    print("Connection closed from server")
    connection = False
    return

def close_conn(s):
    SYN = (str(0) + ";").encode('utf-8')
    FIN = (str(1) + ";").encode('utf-8')
    seqnum = (str(0)).encode('utf-8')
    close_pkt = SYN + FIN + seqnum
    t = threading.Thread(target=recvFIN, args=(r,))
    t.start()
    s.sendto(close_pkt, r_addr)
    print("Connection Close request sent to Server.")
    while connection :
        print(close_pkt)
        start = time.time()
        while time.time() - start < RTO:
                if not connection:
                    break
        if connection:
            print("Connection Close request re-sent to Server.")
            s.sendto(close_pkt,r_addr)
    return

MSS = 2048
N = 100
RTO = 0.1
FORMAT = 'utf-8'

inp_filename = r"CS3543_100MB"
#inp_filename = r"D:\Home\Computer Science\Computer Networks\inp_.txt"

# Create a socket object
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Define the port on which you want to connect
S_IP = '192.168.0.5'
S_PORT = 5051

#the port on which the client receives ack from the server
R_IP = '192.168.0.5'
R_PORT = 10001

r_addr = (S_IP,S_PORT)  #the server address

# connect to the server on local computer
s.connect((S_IP, S_PORT))

r = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
r.bind((R_IP, R_PORT))

ACK = {}
lock = threading.Lock()
expected_ack = 0
check_timeout = 0

data = packetseg(inp_filename,MSS)
#print(data)
print(len(data))
sendSYN(s)
start = time.time()
send(data,N,r_addr)
end = time.time()

print("Time taken to transfer the file: " + str(end - start))
print("Throughtput is: " + str(os.path.getsize(inp_filename)/(end - start)))
close_conn(s)
