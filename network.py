'''
Created on Oct 12, 2016

@author: mwitt_000
'''
import queue
import threading
from _collections import defaultdict


## wrapper class for a queue of packets
class Interface:
    ## @param maxsize - the maximum size of the queue storing packets
    def __init__(self, maxsize=0):
        self.queue = queue.Queue(maxsize);
        self.mtu = None
    
    ##get packet from the queue interface
    def get(self):
        try:
            return self.queue.get(False)
        except queue.Empty:
            return None
        
    ##put the packet into the interface queue
    # @param pkt - Packet to be inserted into the queue
    # @param block - if True, block until room in queue, if False may throw queue.Full exception
    def put(self, pkt, block=False):
        self.queue.put(pkt, block)
        
## Implements a network layer packet (different from the RDT packet 
# from programming assignment 2).
# NOTE: This class will need to be extended to for the packet to include
# the fields necessary for the completion of this assignment.
class NetworkPacket:
    ## packet encoding lengths 
    dst_addr_S_length = 8
    
    ##@param dst_addr: address of the destination host
    # @param data_S: packet payload
    def __init__(self, dst_addr, data_S, identification = None, parent = None, flag = None, source_addr = None, offset = None):
        self.identification = identification
        self.parent = parent
        self.flag = flag
        self.source_addr = source_addr
        self.offset = offset
        self.dst_addr = dst_addr
        self.data_S = data_S
        
    ## called when printing the object
    def __str__(self):
        return self.to_byte_S()
        
    ## convert packet to a byte string for transmission over links
    def to_byte_S(self):
        # Check identification
        if self.identification is None:
            byte_S = str(0)
        else:
            byte_S = str(self.identification)    
            
        # Check parent
        if self.parent is None:
            byte_S += str(0) + str(0)
        else:
            if self.parent < 10:
                byte_S += str(0)
            byte_S += str(self.parent)
    
        #Check flag
        if self.flag is None:
            byte_S += str(0)
        else:
            byte_S += str(self.flag)
           
        # Check offset 
        if self.offset is None:
            byte_S += str(0)
        else:
            byte_S += str(self.offset)
            
        # Check source_addr
        if self.source_addr is None:
            byte_S += str(0)
        else:
            byte_S += str(self.source_addr)
        
        byte_S += str(self.dst_addr)
        byte_S = byte_S.zfill(self.dst_addr_S_length)
        byte_S += self.data_S
        return byte_S
    
    ## extract a packet object from a byte string
    # @param byte_S: byte string representation of the packet
    @classmethod
    def from_byte_S(self, byte_S):
        dst_addr = int(byte_S[7 : NetworkPacket.dst_addr_S_length])
        data_S = byte_S[NetworkPacket.dst_addr_S_length : ]
        identification = int(byte_S[:2])
        parent = int(byte_S[2:4])
        flag = int(byte_S[4:5])
        offset = int(byte_S[5:6])
        source_addr = int(byte_S[6:7])
        return self(dst_addr, data_S, identification, parent, flag, source_addr, offset)
    

    

## Implements a network host for receiving and transmitting data
class Host:
    
    fragmented_packets = defaultdict(list)
    floating_packets = []
    header_length = 8
    
    ##@param addr: address of this node represented as an integer
    def __init__(self, addr):
        self.addr = addr
        self.in_intf_L = [Interface()]
        self.out_intf_L = [Interface()]
        self.stop = False #for thread termination
    
    ## called when printing the object
    def __str__(self):
        return 'Host_%s' % (self.addr)
       
    ## create a packet and enqueue for transmission
    # @param dst_addr: destination address for the packet
    # @param data_S: data being transmitted to the network layer
    def udt_send(self, dst_addr, data_S):
        while data_S is not '':
            p = NetworkPacket(dst_addr, data_S[:40])
            self.out_intf_L[0].put(p.to_byte_S()) #send packets always enqueued successfully
            print('%s: sending packet "%s" out interface with mtu=%d' % (self, p, self.out_intf_L[0].mtu))
            data_S = data_S[40:]
        
    ## receive packet from the network layer
    def udt_receive(self):
        pkt_S = self.in_intf_L[0].get()
        if pkt_S is not None:
            key = self.parse_packet(pkt_S)
            
        
     
    def parse_packet(self, p):
        header = p[:self.header_length]
        message = p[self.header_length:]
        
        key = str(header[6:7]) + str(header[2:4])
        
        if self.fragmented_packets.get(key) is None:
            self.fragmented_packets[key] = []
        
        self.fragmented_packets[key].append(str(header[5:6]) + message)
        
        if header[4:5] is '0':
            self.check_completeness(key)
        
        return key
        
    def check_completeness(self, key):
        # Create temporary list for removal
        temp_fragments = self.fragmented_packets.get(key)
        finished_message = ''
        current_offset = 1
        
        # end if we have found all of the packets
        while len(temp_fragments) is not 0:
            temp_offset = current_offset
            for x in temp_fragments:
                # Check if the offset matches any currently stored fragment
                if int(x[:1]) is current_offset:
                    finished_message += x[1:]
                    current_offset += 1
                    temp_fragments.remove(x)
                    break
                
            # Fail if we've gone through an iteration without finding the next sequential fragment
            # i.e we are missing some fragments
            if temp_offset == current_offset:
                return
        print()
        print('All packets received from source %d with parent datagram %d' % (int(key[:1]) , int(key[1:])))  
        print('%s: received packet "%s"' % (self, finished_message))
    ## thread target for the host to keep receiving data
    def run(self):
        print (threading.currentThread().getName() + ': Starting')
        while True:
            #receive data arriving to the in interface
            self.udt_receive()
            #terminate
            if(self.stop):
                print (threading.currentThread().getName() + ': Ending')
                return
        


## Implements a multi-interface router described in class
class Router:
    
    # Max packet length is max_message_lenght + header = 25
    max_message_length = 20
    current_packet = 1
    header_length = 8
    
    ##@param name: friendly router name for debugging
    # @param intf_count: the number of input and output interfaces 
    # @param max_queue_size: max queue length (passed to Interface)
    def __init__(self, name, intf_count, max_queue_size):
        self.stop = False #for thread termination
        self.name = name
        #create a list of interfaces
        self.in_intf_L = [Interface(max_queue_size) for _ in range(intf_count)]
        self.out_intf_L = [Interface(max_queue_size) for _ in range(intf_count)]

    ## called when printing the object
    def __str__(self):
        return 'Router_%s' % (self.name)

    ## look through the content of incoming interfaces and forward to
    # appropriate outgoing interfaces
    def forward(self):
        for i in range(len(self.in_intf_L)):
            pkt_S = None
            try:
                #get packet from interface i
                pkt_S = self.in_intf_L[i].get()
                #if packet exists make a forwarding decision
                if pkt_S is not None:
                    # Split the header from the message
                    header = pkt_S[:self.header_length]
                    pkt_S = pkt_S[self.header_length:]
                    
                    # Fragment information
                    parent_packet = self.current_packet
                    offset = 1
                    
                    # Continue until there are no more fragments to send
                    while pkt_S is not '':
                        
                        # Flag this fragment as the last for a particular datagram
                        if pkt_S[self.max_message_length:] is '':
                            flag = 0
                        else:
                            flag = 1
                        
                        # New packet to send   
                        p_string = self.remake_header(header, parent_packet, flag, offset, i) + pkt_S[:self.max_message_length]
                        
                        p = NetworkPacket.from_byte_S(p_string) #parse a packet out
                        # HERE you will need to implement a lookup into the 
                        # forwarding table to find the appropriate outgoing interface
                        # for now we assume the outgoing interface is also i
                        self.out_intf_L[i].put(p.to_byte_S(), True)
                        print('%s: forwarding packet "%s" from interface %d to %d with mtu %d' \
                              % (self, p, i, i, self.out_intf_L[i].mtu))
                        
                        # Slice the current packet message and increment counters for next fragment
                        pkt_S = pkt_S[self.max_message_length:]
                        offset += 1
                        self.current_packet += 1
            except queue.Full:
                print('%s: packet "%s" lost on interface %d' % (self, p, i))
                pass
    
    # After the router receives a message from the host, the header is remade with current router information
    def remake_header(self, header, parent_packet, flag, offset, source):
        new_header = str(self.current_packet)
        
        # append an extra zero if not double digits
        if int(parent_packet) < 10:
            new_header += str(0)
        new_header += str(parent_packet)
        new_header += str(flag)
        new_header += str(offset)
        new_header += str(source)
        new_header += str(header[7:8])
        new_header = new_header.zfill(self.header_length)
        return new_header
                
    ## thread target for the host to keep forwarding data
    def run(self):
        print (threading.currentThread().getName() + ': Starting')
        while True:
            self.forward()
            if self.stop:
                print (threading.currentThread().getName() + ': Ending')
                return 