import TL.TransportLayer as tl
import threading
import time


class App_Interface(tl.RDT):

    def __init__(self):
        super(App_Interface, self).__init__()

    def send(self, sskt, filename, r_addr, r):  # To be run by the client.
        base = 0
        nextseq = 0
        packets = tl.Packet()
        data = packets.prepare(filename)
        datasize = len(data)
        print(datasize)
        t = threading.Thread(target=self.receive_ack, args=(datasize, r, ))
        t.start()
        threads = {}
        while nextseq != datasize:
            while (nextseq < base + self.N) and (nextseq != datasize):
                pkt = data[nextseq]
                # send packets using threads to improve speed
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
            #print(len(pkt[0].split(b';')))
            #SYN, FIN, seqnum, _ = pkt[0].split(b';')
            seqnum = pkt[0].split(b';')[2]
            seqnum = int(seqnum)
            #print("Recieved not yet: " + str(seqnum))
            # check if the ack is within or lower than the window
            # if(seqnum < max(ACK.keys())):
            if self.ACK[seqnum] is False:
                #print("Recieved " + str(seqnum))
                self.ACK[seqnum] = True
                true_count += 1
        return

    def send_ack(self, rskt, clt_send_addr):  # To be run by the server.
        FIN = 0
        buffer = {}

        while FIN != 1:
            # Sends a thanking message to the client (encoding to send via a byte-stream).
            #print("Less GOOO")
            ack = rskt.recvfrom(self.MSS)
            start = time.time()
            #print(ack)
            #print("Less GOOO 2")
            #print(ack)
            rcpk = ack[0].split(b';', 3) 
            SYN = rcpk[0]
            SYN = int(SYN)
            FIN = rcpk[1]
            FIN = int(FIN)
            seqnum = rcpk[2]
            seqnum = int(seqnum)
            if FIN == 0 and SYN == 0:
                #buffer[seqnum] = rcpk[3:]
                #if seqnum%1000 == 0:
                #print(seqnum) 
                buffer[seqnum] = b""
                buffer[seqnum] = buffer[seqnum].join(rcpk[3:])
                #print(buffer[seqnum])
                send_ack = tl.Packet()
                send_ack.seqnum = str(seqnum).encode('utf-8')
                send_ack = send_ack.prepare("")
                rskt.sendto(send_ack, clt_send_addr)

            else:
                print(ack[0])
                rskt.sendto(ack[0], clt_send_addr)

            end = time.time()
            #print("Time taken = " + str(end - start))
        print("Server in passive state.")
        rskt.close()
        return buffer# ??

    def timer(self, sskt, pkt, addr, seqnum):  # A - Acknowledgement, L - Loss detection, R - Retransmission.
        while True:
            start = time.time()
            # start = curr
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

    def __init__(self):
        self.start_time = 0
        self.base = 0
        self.next_seq = 0
        self.alpha = 0.125
        self.beta = 0.25
        self.estimated_rtt = 0
        self.dev_rtt = 0
        self.timestamp = {}
        super(TCPML, self).__init__()

    def send(self, sskt, filename, r_addr, r):
        self.next_seq = 0
        packets = tl.Packet()
        data = packets.prepare(filename)
        datasize = len(data)

        receiving_thread = threading.Thread(target=self.receive_ack, args=(datasize, r, sskt))
        receiving_thread.start()
        
        for i in range(0, datasize):
            self.ACK[i] = 0
        
        while self.next_seq != datasize:
            self.ACK[self.next_seq] = 0
            if self.start_time == 0:
                timer_thread = threading.Thread(target=self.timer, args=(sskt, data[self.base], r_addr))
                timer_thread.start()

            while self.next_seq - self.base + 1 <= self.cwnd/self.MSS:
                self.lock.acquire()
                self.timestamp[self.next_seq] = time.time()
                print("Sending: " + str(self.next_seq))
                sskt.sendto(data[self.next_seq], r_addr)
                self.next_seq += 1
                self.lock.release()
                
        
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
            if FIN == 0 and SYN == 0:
                if seqnum == wanted_seq_num:
                    wanted_seq_num += 1
                buffer[seqnum] = rpkt[3:]
                send_ack = tl.Packet()
                send_ack.seqnum = str(wanted_seq_num).encode('utf-8')
                send_ack = send_ack.prepare("")
                rskt.sendto(send_ack, clt_send_addr)
            else:
                print(ack[0])
                rskt.sendto(ack[0], clt_send_addr)

        ordered_seq = sorted(buffer.keys())
        data = buffer[ordered_seq[0]].encode('utf-8')

        for seq in range(1, len(ordered_seq)):
            data += buffer[seq].encode('utf-8')

        print("Server in passive state.")
        rskt.close()
        return  # ??

    def receive_ack(self, datasize, r, sskt):
        true_count = 0
        while true_count != datasize:
            pkt = r.recvfrom(self.MSS)
            curr_time = time.time()
            #SYN, FIN, seqnum,_ = pkt[0].split(b';')
            seqnum = pkt[0].split(b';')[2]
            seqnum = int(seqnum)
            print("Recieved yet to be : " + str(seqnum))
            # check if the ack is within or lower than the window
            # if(seqnum < max(ACK.keys())):
            print(seqnum, self.base , sep = "   ")
            if seqnum > self.base:
                self.lock.acquire()
                sample_rtt = curr_time - self.timestamp[seqnum-1]
                self.estimated_rtt = (1-self.alpha)*self.estimated_rtt + self.alpha*sample_rtt
                self.dev_rtt = (1-self.beta)*self.dev_rtt + self.beta*abs(sample_rtt-self.estimated_rtt)
                self.RTO = self.estimated_rtt + 4*self.dev_rtt
                for index in range(self.base, seqnum):
                    if self.ACK[index] == 0:
                        true_count += 1
                    self.ACK[index] += 1
                    print(index, self.ACK[index], sep = " |||  ")
                self.base = seqnum

                if self.base == self.next_seq:
                    self.start_time = 0
                else:
                    self.start_time = time.time()

                if self.congested == self.SLOW_START:
                    self.cwnd += self.MSS
                elif self.congested == self.CONGESTION_AVOIDANCE:
                    self.cwnd += self.MSS * (self.MSS/self.cwnd)
                else:
                    self.congested = self.CONGESTION_AVOIDANCE
                    self.cwnd = self.ssthresh

                self.lock.release()
            else:
                assert(seqnum == self.base)
                print("Here " + str(seqnum))
                self.ACK[seqnum] += 1
                print()
                if self.ACK[seqnum] == 3:
                    self.lock.acquire()
                    sskt.sendto(pkt, r)
                    self.lock.release()
                    self.congested = self.FAST_RECOVERY
                    self.ssthresh = self.cwnd / 2
                    self.cwnd = self.ssthresh + 3*self.MSS
        return

    def timer(self, sskt, pkt, addr):  # A - Acknowledgement, L - Loss detection, R - Retransmission.
        self.start_time = time.time()
        while True:
            # start = curr
            self.start_time = time.time()
            while time.time() - self.start_time < self.RTO:
                if self.ACK[self.base]:
                    return
            self.lock.acquire()
            self.ssthresh = self.cwnd / 2
            self.cwnd = self.MSS
            self.congested = self.SLOW_START
            self.RTO = self.RTO*2
            sskt.sendto(pkt, addr)  # Retransmission in case of timeout.
            self.start_time = 0
            self.lock.release()
