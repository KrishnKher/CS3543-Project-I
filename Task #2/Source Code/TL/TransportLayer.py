import socket
import logging
import time
import threading
import sys


class RDT:

    CONGESTION_AVOIDANCE = -1
    SLOW_START = 0
    FAST_RECOVERY = 1

    def __init__(self):
        self.MSS = 2048
        self.N = 100  # Window size.
        self.RTO = 0.1  # Timeout (secs).
        self.connection = False
        self.ACK = {}
        self.lock = threading.Lock()
        self.cwnd = self.MSS
        self.rwnd = b""
        self.ssthresh = 32 * 1024
        self.congested = self.SLOW_START  #

    def sendSYN(self, sskt, r, r_addr):
        conn_pkt = Packet()
        conn_pkt.SYN = (str(1) + ";").encode('utf-8')
        t = threading.Thread(target=self.recvSYN, args=(r,))
        t.start()
        conn_pkt = conn_pkt.prepare("")
        sskt.sendto(conn_pkt, r_addr)
        #print("Are you here?")
        while not self.connection:
            #print(conn_pkt)
            start = time.time()
            while time.time() - start < self.RTO:
                if self.connection:
                    break
            if not self.connection:
                sskt.sendto(conn_pkt, r_addr)
        print("Connection request sent to server.")
        return

    def recvSYN(self, r):
        SYN = 0
        while SYN != 1:
            pkt = r.recvfrom(self.MSS)
            print(pkt)
            #SYN, FIN, seqnum, _ = 
            SYN = pkt[0].split(b";")[0]
            SYN = int(SYN)
        print("Connection with server established.")
        self.connection = True
        return

    def recvFIN(self, r):
        FIN = 0
        while FIN != 1:
            pkt = r.recvfrom(self.MSS)
            print(pkt)
            #SYN, FIN, seqnum, _ = 
            FIN = pkt[0].split(b";")[1]
            FIN = int(FIN)
        print("Connection with server closed.")
        self.connection = False
        return

    def close_conn(self, sskt, r, r_addr):
        close_pkt = Packet()
        close_pkt.FIN = (str(1) + ";").encode('utf-8')
        t = threading.Thread(target=self.recvFIN, args=(r,))
        t.start()
        sskt.sendto(close_pkt.prepare(""), r_addr)
        print("Connection-close request sent to server.")
        while self.connection:
            #print(close_pkt)
            start = time.time()
            while time.time() - start < self.RTO:
                if not self.connection:
                    break
            if self.connection:
                sskt.sendto(close_pkt.prepare(""), r_addr)
        return


class Packet(RDT):

    def __init__(self):
        self.SYN = (str(0) + ";").encode('utf-8')
        self.FIN = (str(0) + ";").encode('utf-8')
        self.seqnum = (str(0) + ";").encode('utf-8')
        self.header_size = 0
        super(Packet, self).__init__()

    def prepare(self, i_filename):
        seqcount = 0
        if len(i_filename) > 0:
            ifile = open(i_filename, 'rb')
            self.header_size = sys.getsizeof(self.SYN + self.FIN + self.seqnum)

            data = []
            byte = ifile.read(self.MSS - self.header_size)
            while byte:
                self.seqnum = (str(seqcount) + ";").encode('utf-8')
                data.append(self.SYN + self.FIN + self.seqnum + byte)
                self.header_size = sys.getsizeof(self.SYN + self.FIN + self.seqnum)
                byte = ifile.read(self.MSS - self.header_size)
                seqcount += 1
            ifile.close()
            return data
        else:
            self.seqnum = b"0"
            return self.SYN + self.FIN + self.seqnum
