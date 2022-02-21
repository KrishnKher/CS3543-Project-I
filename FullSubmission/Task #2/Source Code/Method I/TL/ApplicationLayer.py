from concurrent.futures import thread
import queue
import TL.TransportLayer as tl
import threading
import time
import sys
import heapq

class App_Interface(tl.RDT):

    def __init__(self):
        super(App_Interface, self).__init__()

    def send(self, sskt, filename, r_addr, r):  # To be run by the client.
        base = 0
        nextseq = 0
        packets = tl.Packet()
        data = packets.prepare(filename)
        datasize = len(data)
        t = threading.Thread(target=self.receive_ack, args=(datasize, r, ))
        t.start()
        threads = {}
        while nextseq != datasize:
            while (nextseq < base + self.N) and (nextseq != datasize):
                pkt = data[nextseq]
                self.lock.acquire()
                self.ACK[nextseq] = False
                sskt.sendto(pkt, r_addr)
                self.lock.release()
                threads[nextseq] = threading.Thread(target=self.timer, args=(sskt, pkt, r_addr, nextseq))
                threads[nextseq].start()
                nextseq += 1
            while not self.ACK[base]:
                pass
            #self.ACK.pop(base)
            threads[base].join()
            base += 1
        t.join()
        return

    def receive_ack(self, datasize, r):  # To be run by the client.

        true_count = 0
        while true_count != datasize:
            pkt = r.recvfrom(self.MSS)
            seqnum = pkt[0].split(b';')[2]
            seqnum = int(seqnum)
            if self.ACK[seqnum] is False:
                self.ACK[seqnum] = True
                true_count += 1
        return

    def send_ack(self, rskt, clt_send_addr):  # To be run by the server.
        FIN = 0
        buffer = {}

        while FIN != 1:
            # Sends a thanking message to the client (encoding to send via a byte-stream).
            ack = rskt.recvfrom(self.MSS)
            start = time.time()
            rcpk = ack[0].split(b';', 3) 
            SYN = rcpk[0]
            SYN = int(SYN)
            FIN = rcpk[1]
            FIN = int(FIN)
            seqnum = rcpk[2]
            seqnum = int(seqnum)
            if FIN == 0 and SYN == 0:
                buffer[seqnum] = b""
                buffer[seqnum] = buffer[seqnum].join(rcpk[3:])
                send_ack = tl.Packet()
                send_ack.seqnum = str(seqnum).encode('utf-8')
                send_ack = send_ack.prepare("")
                rskt.sendto(send_ack, clt_send_addr)

            else:
                print(ack[0])
                rskt.sendto(ack[0], clt_send_addr)

            end = time.time()
        print("Server in passive state.")
        rskt.close()
        return buffer

    def timer(self, sskt, pkt, addr, seqnum):  # A - Acknowledgement, L - Loss detection, R - Retransmission.
        while True:
            start = time.time()
            while time.time() - start < self.RTO:
                if self.ACK[seqnum]:
                    return
            self.lock.acquire()
            self.ssthresh = self.cwnd/2
            self.cwnd = self.MSS
            self.congested = self.SLOW_START
            print("Timeout for " + str(seqnum))
            sskt.sendto(pkt, addr)  # Retransmission in case of timeout.
            self.lock.release()


class TCPML(App_Interface):

    SENT = 1
    TIMEOUT = 2
    RECEIVED = 3
    NONE = -1

    def __init__(self):
        self.start_time = 0
        self.base = 0
        self.next_seq = 0
        self.alpha = 0.125
        self.beta = 0.25
        self.estimated_rtt = 0
        self.dev_rtt = 0
        self.timestamp = {}
        self.timer_thread = ""
        self.data = {}
        self.datasize = 0
        self.filepointer = None
        self.sent_time = {}
        self.queue = {}
        self.true_count = 0
        self.event = self.SENT
        self.queue_lock = threading.Lock()
        self.event_lock = threading.Lock()
        super(TCPML, self).__init__()

    def send(self, sskt, filename, r_addr, r):
        packets = tl.Packet()
        data = packets.prepare(filename)
        self.datasize = len(data)
        #print(self.datasize)
        self.filepointer = open(filename, 'rb')

        self.next_seq = 0
        
        self.queue[0] = self.SENT

        for i in range(0, self.datasize):           
            self.sent_time[i] = 0

        receiving_thread = threading.Thread(target=self.receive_ack, args=(r, sskt, r_addr))
        receiving_thread.start()

        get_pck = threading.Thread(target=self.get_packet)
        get_pck.start()

        send_pck = threading.Thread(target=self.send_tcp, args=(sskt, r_addr))
        send_pck.start()
        
        #while self.next_seq != self.datasize:
        while self.true_count != self.datasize:
            #print("1 MAIN")
            self.event_lock.acquire()
            first_key = next(iter(self.queue))                
            self.event = self.queue[first_key]
            self.event_lock.release()
            #print("2 MAIN")
            self.queue_lock.acquire()
            del self.queue[first_key]
            print("MAIN ", self.queue, self.true_count)
            self.queue_lock.release()
            #print("3 MAIN")
            print("Executing event:   ", self.event)
            while self.event != self.NONE:
                continue
            #print("4 MAIN")
        receiving_thread.join()
        get_pck.join()
    
    def get_packet(self):
        SYN = (str(0) + ";").encode('utf-8')
        FIN = (str(0) + ";").encode('utf-8')
        seqnum = (str(0) + ";").encode('utf-8')
        seqcount = 0
        header_size = sys.getsizeof(SYN + FIN + seqnum)    
        byte = self.filepointer.read(self.MSS - header_size)
        while byte:
            seqnum = (str(seqcount) + ";").encode('utf-8')
            #data.append(SYN + FIN + seqnum + byte)
            self.data[seqcount] = SYN + FIN + seqnum + byte
            self.queue_lock.acquire()
            self.queue[time.time()] = (self.SENT)
            print("SEND ", self.queue, self.true_count)
            self.queue_lock.release()
            header_size = sys.getsizeof(SYN + FIN + seqnum)
            byte = self.filepointer.read(self.MSS - header_size)
            seqcount += 1
        self.filepointer.close()

    def send_tcp(self, sskt, r_addr):
        #self.next_seq = 0
        #packets = tl.Packet()
        #self.data = packets.prepare(filename)
        #datasize = len(self.data)

        #receiving_thread = threading.Thread(target=self.receive_ack, args=(datasize, r, sskt, r_addr))
        #receiving_thread.start()
        
        #print("1 SENDTO")
        while self.next_seq != self.datasize:
            #print("2 SENDTO")
            while self.event != self.SENT:
                continue
            #print("3 SENDTO")
            self.ACK[self.next_seq] = 0
            if self.start_time == 0:
                #print("4 SENDTO")
                if self.base == 0:
                    while self.base not in self.data:
                        continue
                self.timer_thread = threading.Thread(target=self.timer, args=(sskt, self.data[self.base], r_addr))
                self.timer_thread.start()

            if (self.next_seq - self.base + 1 <= self.cwnd/self.MSS + 5) and (self.next_seq != self.datasize):
                #self.ACK[self.next_seq] = 0
                #print("5 SENDTO")
                self.lock.acquire()
                self.ACK[self.next_seq] = 0
                self.timestamp[self.next_seq] = time.time()
                #print("Sending: " + str(self.next_seq)+ " " + str(time.time()))
                sys.stdout.flush()
                self.sent_time[self.next_seq] = 1
                sskt.sendto(self.data[self.next_seq], r_addr)
                self.next_seq += 1
                self.lock.release()
            
            self.event_lock.acquire()
            self.event = self.NONE
            self.event_lock.release()

            print("1. " + str(self.next_seq) + " 2. " + str(self.base) + " 3. " + str(self.cwnd/self.MSS) + " " + str(time.time()))
            sys.stdout.flush()
              
        return
        #timer_thread.join()

    def send_ack(self, rskt, clt_send_addr):  # To be run by the server.
        buffer = {}
        wanted_seq_num = 0
        FIN = 0

        while FIN != 1:
            # Sends a thanking message to the client (encoding to send via a byte-stream).
            ack = rskt.recvfrom(self.MSS)
            rpkt = ack[0].split(b';', 3)
            SYN = rpkt[0]
            SYN = int(SYN)
            FIN = rpkt[1]
            FIN = int(FIN)
            seqnum = rpkt[2]
            seqnum = int(seqnum)
            print("Recieved: " + str(seqnum) + " " + str(time.time()))
            sys.stdout.flush()
            if FIN == 0 and SYN == 0:
                if seqnum == wanted_seq_num:
                    wanted_seq_num += 1
                buffer[seqnum] = b""
                buffer[seqnum] = buffer[seqnum].join(rpkt[3:])
                send_ack = tl.Packet()
                send_ack.seqnum = str(wanted_seq_num).encode('utf-8')
                send_ack = send_ack.prepare("")
                rskt.sendto(send_ack, clt_send_addr)
                #print("send_ack " +str(send_ack))
            else:
                print(ack[0])
                sys.stdout.flush()
                rskt.sendto(ack[0], clt_send_addr)

        print("Server in passive state.")
        sys.stdout.flush()
        rskt.close()
        return buffer# ??

    def receive_ack(self, r, sskt, r_addr):
        self.true_count = 0
        while self.true_count != self.datasize:
            pkt = r.recvfrom(self.MSS)
            self.queue_lock.acquire()
            self.queue[time.time()] = (self.RECEIVED)
            print("RECIEVE ", self.queue, self.true_count)
            self.queue_lock.release()
            
            while self.event != self.RECEIVED:
                #print("Namaste ji")
                continue
            
            curr_time = time.time()
            #SYN, FIN, seqnum,_ = pkt[0].split(b';')
            seqnum = pkt[0].split(b';')[2]
            seqnum = int(seqnum)
            #print("Recieved yet to be : " + str(seqnum) + " " + str(time.time()))
            sys.stdout.flush()
            # check if the ack is within or lower than the window
            # if(seqnum < max(ACK.keys())):
            #print(seqnum, self.base , sep = "   ")
            if seqnum > self.base:
                #print(seqnum, self.base , sep = " ---  ")
                self.lock.acquire()
                #print("srt " + str(curr_time - self.timestamp[seqnum-1]))
                sample_rtt = min(self.RTO, curr_time - self.timestamp[seqnum-1])
                print("How big you are  " + str(sample_rtt) + " " + str(time.time()))
                sys.stdout.flush()
                self.estimated_rtt = (1-self.alpha)*self.estimated_rtt + self.alpha*sample_rtt
                self.dev_rtt = (1-self.beta)*self.dev_rtt + self.beta*abs(sample_rtt-self.estimated_rtt)
                self.RTO = self.estimated_rtt + 4*self.dev_rtt
                for index in range(self.base, seqnum):
                    if self.ACK[index] == 0:
                        self.true_count += 1
                    self.ACK[index] += 1
                    #print(index, self.ACK[index], sep = " |||  ")
                self.base = seqnum

                # if self.base == self.next_seq:
                #     #print("I am here!!")
                #     self.start_time = 0
                # else:
                #     print("Kaise ho")
                #     if self.start_time != 0:
                #         #self.timer_thread.join()
                #         print("Theek hai")
                #     self.timer_thread = threading.Thread(target=self.timer, args=(sskt, self.data[self.base], r_addr))
                #     self.timer_thread.start()

                #print(">The current con state is ", self.congested, " and ", self.cwnd/self.MSS)
                
                if self.congested == self.SLOW_START:
                    self.cwnd += self.MSS
                    #print(" ss The current con state is ", self.congested, " and ", self.cwnd/self.MSS)
                    sys.stdout.flush()
                elif self.congested == self.CONGESTION_AVOIDANCE:
                    self.cwnd += self.MSS * (self.MSS/self.cwnd)
                    #print(" ca The current con state is ", self.congested, " and ", self.cwnd/self.MSS)
                    sys.stdout.flush()
                else:
                    self.congested = self.CONGESTION_AVOIDANCE
                    self.cwnd = self.ssthresh
                    #print(" @@@ The current con state is ", self.congested, " and ", self.cwnd/self.MSS)
                    sys.stdout.flush()

                self.lock.release()
            else:
                assert(seqnum == self.base)
                #print("Here " + str(seqnum))
                self.ACK[seqnum-1] += 1
                if self.ACK[seqnum-1] == 3:
                    self.lock.acquire()
                    sskt.sendto(pkt, r)
                    self.congested = self.FAST_RECOVERY
                    self.ssthresh = self.cwnd / 2
                    self.cwnd = self.ssthresh + 3*self.MSS
                    #print("<=The current con state is ", self.congested, " and ", self.cwnd/self.MSS)
                    sys.stdout.flush()
                    self.lock.release()
            self.event_lock.acquire()
            self.event = -1
            self.event_lock.release()
        return
    
    def timer(self, sskt, pkt, addr):  # A - Acknowledgement, L - Loss detection, R - Retransmission.
        #self.start_time = time.time()
        while True:
            # start = curr
            temp = self.base
            if self.sent_time[temp] == 0:
                continue

            self.start_time = time.time()
            while time.time() - self.start_time < self.RTO:
                if self.ACK[temp]:
                    self.start_time = 0
                    return

            if self.ACK[temp] > 0:
                if self.base == self.next_seq:
                        #print("I am here!!")
                        self.start_time = 0
                else:
                    #print("Kaise ho")
                    if self.start_time != 0:
                        #self.timer_thread.join()
                        self.start_time = time.time()
                    #self.timer_thread = threading.Thread(target=self.timer, args=(sskt, self.data[self.base], r_addr))
                    #self.timer_thread.start()
                continue
            self.queue_lock.acquire()
            self.queue[time.time()] = self.TIMEOUT
            print("TIMEOUT ", self.queue, self.true_count)
            self.queue_lock.release()

            while self.event != self.TIMEOUT:
                continue
            #print("TIMEOUT!!")
            self.lock.acquire()
            self.ssthresh = self.cwnd / 2
            self.cwnd = self.MSS
            self.congested = self.SLOW_START
            self.RTO = self.RTO*2
            #print("Timeout " + str(temp))
            sys.stdout.flush()
            sskt.sendto(pkt, addr)  # Retransmission in case of timeout.
            #self.start_time = time.time()      #REMEMBER IMPORTANT CRITICAL DANGEROUS
            self.lock.release()
            self.event_lock.acquire()
            self.event = -1
            self.event_lock.release()
