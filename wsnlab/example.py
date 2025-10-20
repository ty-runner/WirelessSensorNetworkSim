import random
from enum import Enum
import sys
# insert at 1, 0 is the script path (or '' in REPL)
sys.path.insert(1, '.')
from source import wsnlab_vis as wsn
import math
from source import config
from collections import Counter
import csv  # <— add this near your other imports

# Track where each node is placed
NODE_POS = {}  # {node_id: (x, y)}

# --- tracking containers ---
ALL_NODES = []              # node objects
CLUSTER_HEADS = []
ROLE_COUNTS = Counter()     # live tally per Roles enum
MAX_NET_NODES = 253 #max number 
Roles = Enum('Roles', 'UNDISCOVERED UNREGISTERED ROOT REGISTERED CLUSTER_HEAD ROUTER GATEWAY')
MESSAGE_TYPES = {
    ### DISCOVERY MSGS
    'PROBE': 'PROBE',
    'HEARTBEAT': 'HEARTBEAT',

    ### CLUSTER MEMBERSHIP MSGS
    'JOIN_REQUEST': 'JOIN_REQUEST',
    'JOIN_ACK': 'JOIN_ACK',
    'JOIN_REPLY': 'JOIN_REPLY',
    'LEAVE': 'LEAVE',
    'ADDRESS_RENEW': 'ADDRESS_RENEW',

    ### CLUSTER CREATION MSGS
    'NETID_REQUEST': 'NETID_REQUEST',
    'NETID_RESPONSE': 'NETID_RESPONSE',
    
    ### ROUTING MSGS
    'TABLE_SHARE': 'TABLE_SHARE',
    'ROUTE_ERROR': 'ROUTE_ERROR',

    ### RELIABILITY
    'ACK': 'ACK',
    'DATA': 'DATA',

    #TODO skipping fragmentation feature for now

    ### Maintainance
    'KEEP_ALIVE': 'KEEP_ALIVE'
}
"""Enumeration of roles"""


###########################################################
class SensorNode(wsn.Node):
    """SensorNode class is inherited from Node class in wsnlab.py.
    It will run data collection tree construction algorithms.

    Attributes:
        role (Roles): role of node
        is_root_eligible (bool): keeps eligibility to be root
        c_probe (int): probe message counter
        th_probe (int): probe message threshold
        received_HB_addresses (List of Addr): keeps the addresses of received heart beat messages
    """

    ###################
    def init(self):
        """Initialization of node. Setting all attributes of node.
        At the beginning node needs to be sleeping and its role should be UNDISCOVERED.

        Args:

        Returns:

        """
        self.scene.nodecolor(self.id, 1, 1, 1) # sets self color to white
        self.sleep()
        self.addr = None
        self.ch_addr = None
        self.parent_gui = None
        self.root_addr = None
        self.set_role(Roles.UNDISCOVERED)
        self.is_root_eligible = True if self.id == ROOT_ID else False
        self.c_probe = 0  # c means counter and probe is the name of counter
        self.th_probe = 10  # th means threshold and probe is the name of threshold
        self.hop_count = 99999
        self.neighbors_table = {}  # keeps neighbor information with received HB messages
        self.candidate_parents_table = []
        self.child_networks_table = {}
        self.members_table = []
        self.received_JR_guis = []  # keeps received Join Request global unique ids
        self.example_counter = 0

    def become_unregistered(self):
        if self.role != Roles.UNDISCOVERED:
            self.kill_all_timers()
            self.log('I became UNREGISTERED')
        self.scene.nodecolor(self.id, 1, 1, 0)
        self.erase_parent()
        self.addr = None
        self.ch_addr = None
        self.parent_gui = None
        self.root_addr = None
        self.net_capacity = 0
        self.set_role(Roles.UNREGISTERED)
        self.c_probe = 0
        self.th_probe = 10
        self.hop_count = 99999
        self.neighbors_table = {}
        self.candidate_parents_table = []
        self.child_networks_table = {}
        self.members_table = []
        self.received_JR_guis = []  # keeps received Join Request global unique ids
        self.send_probe()
        self.set_timer('TIMER_JOIN_REQUEST', 20)
    ###################

    def run(self):
        """Setting the arrival timer to wake up after firing.

        Args:

        Returns:

        """
        self.set_timer('TIMER_ARRIVAL', self.arrival)
    def set_role(self, new_role, *, recolor=True):
        """Central place to switch roles, keep tallies, and (optionally) recolor."""
        old_role = getattr(self, "role", None)
        if old_role is not None:
            ROLE_COUNTS[old_role] -= 1
            if ROLE_COUNTS[old_role] <= 0:
                ROLE_COUNTS.pop(old_role, None)
        ROLE_COUNTS[new_role] += 1
        self.role = new_role

        if recolor:
            if new_role == Roles.UNDISCOVERED:
                self.scene.nodecolor(self.id, 150, 150, 150)
            elif new_role == Roles.UNREGISTERED:
                self.scene.nodecolor(self.id, 1, 0.5, 0)
            elif new_role == Roles.REGISTERED:
                self.scene.nodecolor(self.id, 0, 1, 0)
            elif new_role == Roles.CLUSTER_HEAD:
                self.scene.nodecolor(self.id, 0, 0, 1)
                self.draw_tx_range()
            elif new_role == Roles.ROOT:
                self.scene.nodecolor(self.id, 0, 0, 0)
                #self.draw_tx_range()
                self.set_timer('TIMER_EXPORT_CH_CSV', config.EXPORT_CH_CSV_INTERVAL)
                self.set_timer('TIMER_EXPORT_NEIGHBOR_CSV', config.EXPORT_NEIGHBOR_CSV_INTERVAL)

    ###################
    def update_neighbor(self, pck):
        #if we havent heard from this node before, add to neighbor table
        #if pck['role_type'] == Roles.CLUSTER_HEAD or pck['role_type'] == Roles.ROOT:
        if pck['unique_id'] not in self.candidate_parents_table:
            self.candidate_parents_table.append(pck['unique_id'])
        if pck['unique_id'] not in self.neighbors_table.keys():
            self.neighbors_table[pck['unique_id']] = pck

    def select_and_join(self):
        min_hop = 99999
        min_hop_gui = 99999
        for gui in self.candidate_parents_table:
            if self.neighbors_table[gui]['hop_count'] < min_hop or (self.neighbors_table[gui]['hop_count'] == min_hop and gui < min_hop_gui):
                min_hop = self.neighbors_table[gui]['hop_count']
                min_hop_gui = gui
        selected_addr = self.neighbors_table[min_hop_gui]['source_addr']
        self.send_join_request(selected_addr)
        self.set_timer('TIMER_JOIN_REQUEST', config.JOIN_REQUEST_TIME_INTERVAL)
    # CREATING DEFAULT PACKET STRUCTURE FOR INITIAL APPENDING
    # msg_type | dest_addr | next_hop | source_addr | TTL (hop count) | PAYLOAD 
    def create_pck(self, msg_type, dest, next_hop=None, source_addr=None, hop_count=None, unique_id=None):
        packet = {'msg_type': msg_type, 'dest': dest, 'next_hop': next_hop, 'source_addr': source_addr, 'hop_count': hop_count, 'unique_id': unique_id}
        return packet
    def route_and_forward_package(self, pck):
        """Routing and forwarding given package

        Args:
            pck (Dict): package to route and forward it should contain dest, source and type.
        Returns:

        """

        """
        Logic we want:
        1. Direct delivery: 
            if destID in neighbor table or members table -> next_hop = dest_id
        2. Known Child Cluster:
            if the parent of destID exists in the child next table -> next_hop = destID.parent
        3. Else
            next_hop = self.parent
        """
        #direct delivery:
        #if pck['dest'] == 
        #print(pck['dest'])

        #Send up as an else case
        if self.role != Roles.ROOT:
            pck['next_hop'] = self.neighbors_table[self.parent_gui]['ch_addr']
        #1. Direct Delivery: if in immediate vicinity, route to dest
        if pck['dest'].node_addr in self.neighbors_table or pck['dest'].node_addr in self.members_table: 
            #print("FOUND")
            #print(pck['dest'].node_addr)
            #print(self.neighbors_table)
            pck['next_hop'] = pck['dest']
        #2. 
        if self.ch_addr is not None:
            if pck['dest'].net_addr == self.ch_addr.net_addr:
                pck['next_hop'] = pck['dest']
            else:
                for child_gui, child_networks in self.child_networks_table.items():
                    if pck['dest'].net_addr in child_networks:
                        pck['next_hop'] = self.neighbors_table[child_gui]['addr']
                        break
        
        self.send(pck)
    def send_probe(self): #probe to discover network
        self.send(self.create_pck(msg_type=MESSAGE_TYPES['PROBE'], dest=wsn.BROADCAST_ADDR, unique_id=self.id))
    ###################
    def send_heartbeat(self): #periodic message and response to probes
        self.send({'dest': wsn.BROADCAST_ADDR,
            'msg_type': MESSAGE_TYPES['HEARTBEAT'],
            'source_addr': self.ch_addr if self.ch_addr is not None else self.addr,
            'unique_id': self.id,
            'role_type': self.role,
            'addr': self.addr,
            'ch_addr': self.ch_addr,
            'hop_count': self.hop_count})
    ###################
    def send_join_request(self, selected_parent_addr): #periodic message and response to probes
        self.send({'dest': selected_parent_addr,
            'msg_type': MESSAGE_TYPES['JOIN_REQUEST'],
            'source_addr': self.ch_addr if self.ch_addr is not None else self.addr,
            'unique_id': self.id,
            'hop_count': self.hop_count})
    def send_join_reply(self, gui, addr):
        """Sending join reply message to register the node requested to join.
        The message includes a gui to determine which node will take this reply, an addr to be assigned to the node
        and a root_addr.

        Args:
            gui (int): Global unique ID
            addr (Addr): Address that will be assigned to new registered node
        Returns:

        """
        self.send({'dest': wsn.BROADCAST_ADDR, 'msg_type': MESSAGE_TYPES['JOIN_REPLY'], 'source_addr': self.ch_addr,
                   'unique_id': self.id, 'dest_gui': gui, 'addr': addr, 'root_addr': self.root_addr,
                   'hop_count': self.hop_count+1})

    ###################
    def send_join_ack(self, dest):
        """Sending join acknowledgement message to given destination address.

        Args:
            dest (Addr): Address of destination node
        Returns:

        """
        self.send({'dest': dest, 'msg_type': MESSAGE_TYPES['JOIN_ACK'], 'source_addr': self.addr,
                   'unique_id': self.id})
    ###################
    def send_netid_request(self):
        """Sending network request message to root address to be cluster head

        Args:

        Returns:

        """
        self.route_and_forward_package({'dest': self.root_addr, 'msg_type': 'NETID_REQUEST', 'source': self.addr})
    ###################
    def send_network_reply(self, dest, addr):
        """Sending network reply message to dest address to be cluster head with a new adress

        Args:
            dest (Addr): destination address
            addr (Addr): cluster head address of new network

        Returns:

        """
        self.route_and_forward_package({'dest': dest, 'msg_type': 'NETID_RESPONSE', 'source': self.addr, 'addr': addr})

    ###################
    def on_receive(self, pck):
        if self.role == Roles.UNDISCOVERED:
            if pck['msg_type'] == MESSAGE_TYPES['HEARTBEAT']:
                self.become_unregistered()
                self.kill_timer('TIMER_PROBE')
                self.update_neighbor(pck)
        if self.role == Roles.UNREGISTERED:
            if pck['msg_type'] == MESSAGE_TYPES['HEARTBEAT']:
                self.update_neighbor(pck)
            if pck['msg_type'] == 'JOIN_REPLY':  # it becomes registered and sends join ack if the message is sent to itself once received join reply
                if pck['dest_gui'] == self.id:
                    self.addr = pck['addr']
                    self.parent_gui = pck['unique_id']
                    self.root_addr = pck['root_addr']
                    self.hop_count = pck['hop_count']
                    self.draw_parent()
                    self.kill_timer('TIMER_JOIN_REQUEST')
                    self.send_heartbeat()
                    self.set_timer('TIMER_HEART_BEAT', config.HEART_BEAT_TIME_INTERVAL)
                    self.log("JOIN REPLY")
                    self.log('source addr')
                    self.log(pck['source_addr'])
                    self.send_join_ack(pck['source_addr'])
                    if self.ch_addr is not None: # it could be a cluster head which lost its parent
                        self.set_role(Roles.CLUSTER_HEAD)
                        self.send_network_update()
                    else:
                        self.set_role(Roles.REGISTERED)
        if self.role == Roles.REGISTERED:
            if pck['msg_type'] == MESSAGE_TYPES['PROBE']:
                self.send_heartbeat()
            if pck['msg_type'] == MESSAGE_TYPES['JOIN_REQUEST']:
                self.received_JR_guis.append(pck['unique_id'])
                self.send_netid_request()
            if pck['msg_type'] == MESSAGE_TYPES['NETID_RESPONSE']:
                self.set_role(Roles.CLUSTER_HEAD)
                self.net_capacity = MAX_NET_NODES
                try:
                    write_clusterhead_distances_csv("clusterhead_distances.csv")
                except Exception as e:
                    self.log(f"CH CSV export error: {e}")
                self.scene.nodecolor(self.id, 0, 0, 1)
                self.ch_addr = pck['addr']
                #self.send_network_update()
                # yield self.timeout(.5)
                self.send_heartbeat()
                for gui in self.received_JR_guis:
                    # yield self.timeout(random.uniform(.1,.5))
                    if self.net_capacity > 0:
                        self.log("sending join reply")
                        self.send_join_reply(gui, wsn.Addr(self.ch_addr.net_addr, MAX_NET_NODES - self.net_capacity))
                        self.net_capacity -= 1
                #self.received_JR_guis = [] #reset our jr list
        if self.role == Roles.ROOT or self.role == Roles.CLUSTER_HEAD:  # if the node is root or cluster head
            if ('next_hop' in pck and pck['next_hop'] is not None and pck['dest'] != self.addr and pck['dest'] != self.ch_addr):
                self.route_and_forward_package(pck)
                return
            if pck['msg_type'] == MESSAGE_TYPES['HEARTBEAT']:
                self.update_neighbor(pck)
            if pck['msg_type'] == 'PROBE':  # it waits and sends heart beat message once received probe message
                # yield self.timeout(.5)
                self.send_heartbeat()
            if pck['msg_type'] == MESSAGE_TYPES['JOIN_REQUEST']:  # it waits and sends join reply message once received join request
                if self.net_capacity > 0:
                    #we can add them, send join req reply
                    self.send_join_reply(pck['unique_id'], wsn.Addr(self.ch_addr.net_addr, MAX_NET_NODES - self.net_capacity))
                    self.net_capacity -= 1
            if pck['msg_type'] == MESSAGE_TYPES['NETID_REQUEST']:  # it sends a network reply to requested node
                # yield self.timeout(.5)
                if self.role == Roles.ROOT:
                    new_addr = wsn.Addr(pck['source'].node_addr,254)
                    self.send_network_reply(pck['source'],new_addr)
            if pck['msg_type'] == MESSAGE_TYPES['JOIN_ACK']:
                self.members_table.append(pck['unique_id'])
            if pck['msg_type'] == MESSAGE_TYPES['TABLE_SHARE']:
                self.child_networks_table[pck['unique_id']] = pck['child_networks']
                if self.role != Roles.ROOT:
                    self.send_network_update()
            if pck['msg_type'] == MESSAGE_TYPES['DATA']:
                pass



    ###################
    def on_timer_fired(self, name, *args, **kwargs):
        if name == 'TIMER_ARRIVAL':
            self.wake_up()
            self.log('HELLONODES')
            self.set_timer('TIMER_PROBE', 1)
        elif name == 'TIMER_PROBE':
            if self.c_probe < self.th_probe:
                self.send_probe()
                self.c_probe += 1
                self.set_timer('TIMER_PROBE', 1)
            else: #TODO investigate if it makes sense to also consider moving to clusterhead
                if self.is_root_eligible:
                    #become root!
                    self.set_role(Roles.ROOT)
                    self.net_capacity = MAX_NET_NODES
                    self.addr = wsn.Addr(self.id, 254)
                    self.ch_addr = wsn.Addr(self.id, 254)
                    self.root_addr = self.addr
                    self.hop_count = 0
                    self.set_timer('TIMER_HEARTBEAT', config.HEART_BEAT_TIME_INTERVAL)
                else:
                    #if we can't become root, try and try again!
                    self.c_probe = 0
                    self.set_timer('TIMER_PROBE', config.SLEEP_MODE_PROBE_TIME_INTERVAL)
        elif name == 'TIMER_HEARTBEAT':
            self.send_heartbeat()
            self.set_timer('TIMER_HEARTBEAT', config.HEART_BEAT_TIME_INTERVAL)
        elif name == 'TIMER_JOIN_REQUEST':
            self.log("sending join req")
            if len(self.candidate_parents_table) != 0:
                self.select_and_join()
            else: 
                self.set_timer('TIMER_JOIN_REQUEST', config.JOIN_REQUEST_TIME_INTERVAL)



ROOT_ID = random.randint(0, config.SIM_NODE_COUNT)

def write_node_distances_csv(path="node_distances.csv"):
    """Write pairwise node-to-node Euclidean distances as an edge list."""
    ids = sorted(NODE_POS.keys())
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["source_id", "target_id", "distance"])
        for i, sid in enumerate(ids):
            x1, y1 = NODE_POS[sid]
            for tid in ids[i+1:]:  # i+1 to avoid duplicates and self-pairs
                x2, y2 = NODE_POS[tid]
                dist = math.hypot(x1 - x2, y1 - y2)
                w.writerow([sid, tid, f"{dist:.6f}"])


def write_node_distance_matrix_csv(path="node_distance_matrix.csv"):
    ids = sorted(NODE_POS.keys())
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["node_id"] + ids)
        for sid in ids:
            x1, y1 = NODE_POS[sid]
            row = [sid]
            for tid in ids:
                x2, y2 = NODE_POS[tid]
                dist = math.hypot(x1 - x2, y1 - y2)
                row.append(f"{dist:.6f}")
            w.writerow(row)


def write_clusterhead_distances_csv(path="clusterhead_distances.csv"):
    """Write pairwise distances between current cluster heads."""
    clusterheads = []
    for node in sim.nodes:
        # Only collect nodes that are cluster heads and have recorded positions
        if hasattr(node, "role") and node.role == Roles.CLUSTER_HEAD and node.id in NODE_POS:
            x, y = NODE_POS[node.id]
            clusterheads.append((node.id, x, y))

    if len(clusterheads) < 2:
        # Still write the header so the file exists/is refreshed
        with open(path, "w", newline="") as f:
            csv.writer(f).writerow(["clusterhead_1", "clusterhead_2", "distance"])
        return

    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["clusterhead_1", "clusterhead_2", "distance"])
        for i, (id1, x1, y1) in enumerate(clusterheads):
            for id2, x2, y2 in clusterheads[i+1:]:
                dist = math.hypot(x1 - x2, y1 - y2)
                w.writerow([id1, id2, f"{dist:.6f}"])



def write_neighbor_distances_csv(path="neighbor_distances.csv", dedupe_undirected=True):
    """
    Export neighbor distances per node.
    Each row is (node -> neighbor) with distance from NODE_POS.

    Args:
        path (str): output CSV path
        dedupe_undirected (bool): if True, writes each unordered pair once
                                  (min(node_id,neighbor_id), max(...)).
                                  If False, writes one row per direction.
    """
    # Safety: ensure we can compute distances
    if not globals().get("NODE_POS"):
        raise RuntimeError("NODE_POS is missing; record positions during create_network().")

    # Prepare a set to avoid duplicates if dedupe_undirected=True
    seen_pairs = set()

    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["node_id", "neighbor_id", "distance",
                    "neighbor_role", "neighbor_hop_count", "arrival_time"])

        for node in sim.nodes:
            # Skip nodes without any neighbor info yet
            if not hasattr(node, "neighbors_table"):
                continue

            x1, y1 = NODE_POS.get(node.id, (None, None))
            if x1 is None:
                continue  # no position → cannot compute distance

            # neighbors_table: key = neighbor GUI, value = heartbeat packet dict
            for n_gui, pck in getattr(node, "neighbors_table", {}).items():
                # Optional dedupe (unordered)
                if dedupe_undirected:
                    key = (min(node.id, n_gui), max(node.id, n_gui))
                    if key in seen_pairs:
                        continue
                    seen_pairs.add(key)

                # Position of neighbor
                x2, y2 = NODE_POS.get(n_gui, (None, None))
                if x2 is None:
                    continue

                # Distance (prefer pck['distance'] if you added it in update_neighbor)
                dist = pck.get("distance")
                if dist is None:
                    dist = math.hypot(x1 - x2, y1 - y2)

                # Extra fields (best-effort; may be missing)
                n_role = getattr(pck.get("role", None), "name", pck.get("role", None))
                hop = pck.get("hop_count", "")
                at  = pck.get("arrival_time", "")

                w.writerow([node.id, n_gui, f"{dist:.6f}", n_role, hop, at])
###########################################################
def create_network(node_class, number_of_nodes=100):
    """Creates given number of nodes at random positions with random arrival times.

    Args:
        node_class (Class): Node class to be created.
        number_of_nodes (int): Number of nodes.
    Returns:

    """
    edge = math.ceil(math.sqrt(number_of_nodes))
    for i in range(number_of_nodes):
        x = i / edge
        y = i % edge
        px = 50 + x * config.SIM_NODE_PLACING_CELL_SIZE + random.uniform(-1 * config.SIM_NODE_PLACING_CELL_SIZE / 3, config.SIM_NODE_PLACING_CELL_SIZE / 3)
        py = 50 + y * config.SIM_NODE_PLACING_CELL_SIZE + random.uniform(-1 * config.SIM_NODE_PLACING_CELL_SIZE / 3, config.SIM_NODE_PLACING_CELL_SIZE / 3)
        node = sim.add_node(node_class, (px, py))
        node.tx_range = config.NODE_TX_RANGE
        node.logging = True
        node.arrival = random.uniform(0, config.NODE_ARRIVAL_MAX)


sim = wsn.Simulator(
    duration=config.SIM_DURATION,
    timescale=config.SIM_TIME_SCALE,
    visual=config.SIM_VISUALIZATION,
    terrain_size=config.SIM_TERRAIN_SIZE,
    title=config.SIM_TITLE)

# creating random network
create_network(SensorNode, config.SIM_NODE_COUNT)

# start the simulation
sim.run()

# Created 100 nodes at random locations with random arrival times.
# When nodes are created they appear in white
# Activated nodes becomes red
# Discovered nodes will be yellow
# Registered nodes will be green.
# Root node will be black.
# Routers/Cluster Heads should be blue
