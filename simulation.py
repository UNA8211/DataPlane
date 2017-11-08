'''
Created on Oct 12, 2016

@author: mwitt_000
'''
import network
import link
import threading
from time import sleep
from collections import defaultdict

##configuration parameters
router_queue_size = 0 #0 means unlimited
simulation_time = 1 #give the network sufficient time to transfer all packets before quitting

# creates a routing table from a sequence of src-addr/dst-link pairings
def createRoutingTable(seq):
    d = defaultdict(int)
    for k, v in seq:
        d[k] = v

    return d

if __name__ == '__main__':
    object_L = [] #keeps track of objects, so we can kill their threads

    #create network nodes
    client1 = network.Host(1)
    object_L.append(client1)
    client2 = network.Host(2)
    object_L.append(client2)
    server1 = network.Host(3)
    object_L.append(server1)
    server2 = network.Host(4)
    object_L.append(server2)

    router_a = network.Router(name='A', intf_count=2, max_queue_size=router_queue_size, routing_table=createRoutingTable([(1,0), (2,1)])) # fwd 1 thru B and 2 thru C
    object_L.append(router_a)
    router_b = network.Router(name='B', intf_count=1, max_queue_size=router_queue_size, routing_table=createRoutingTable([(1,0)])) # fwd 1 to D
    object_L.append(router_b)
    router_c = network.Router(name='C', intf_count=1, max_queue_size=router_queue_size, routing_table=createRoutingTable([(2,0)])) # fwd 2 to D
    object_L.append(router_c)
    router_d = network.Router(name='D', intf_count=2, max_queue_size=router_queue_size, routing_table=createRoutingTable([(1,0), (2,1)])) # fwd 1 to 3 and 2 to 4
    object_L.append(router_d)

    #create a Link Layer to keep track of links between network nodes
    link_layer = link.LinkLayer()

    #add all the links
    link_layer.add_link(link.Link(client1, 0, router_a, 0, 50))
    link_layer.add_link(link.Link(client2, 0, router_a, 1, 50))

    link_layer.add_link(link.Link(router_a, 0, router_b, 0, 50))
    link_layer.add_link(link.Link(router_a, 1, router_c, 0, 50))
    link_layer.add_link(link.Link(router_b, 0, router_d, 0, 50))
    link_layer.add_link(link.Link(router_c, 0, router_d, 1, 50))

    link_layer.add_link(link.Link(router_d, 0, server1, 0, 50))
    link_layer.add_link(link.Link(router_d, 1, server2, 0, 50))

    #start all the objects
    thread_L = []
    thread_L.append(threading.Thread(name=client1.__str__(), target=client1.run))
    thread_L.append(threading.Thread(name=server1.__str__(), target=server1.run))
    thread_L.append(threading.Thread(name=client2.__str__(), target=client2.run))
    thread_L.append(threading.Thread(name=server2.__str__(), target=server2.run))

    thread_L.append(threading.Thread(name=router_a.__str__(), target=router_a.run))
    thread_L.append(threading.Thread(name=router_b.__str__(), target=router_b.run))
    thread_L.append(threading.Thread(name=router_c.__str__(), target=router_c.run))
    thread_L.append(threading.Thread(name=router_d.__str__(), target=router_d.run))

    thread_L.append(threading.Thread(name="Network", target=link_layer.run))

    for t in thread_L:
        t.start()
    print("happy6")

    #create some send events
    for i in range(3):
        print("p")
        client1.udt_send(3, 'Sending a much larger message this time for the first part of the thing %d' % i)


    #give the network sufficient time to transfer all packets before quitting
    sleep(simulation_time)

    #join all threads
    for o in object_L:
        o.stop = True
    for t in thread_L:
        t.join()

    print("All simulation threads joined")
