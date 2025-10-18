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
Roles = Enum('Roles', 'UNDISCOVERED UNREGISTERED ROOT REGISTERED CLUSTER_HEAD ROUTER GATEWAY')
MESSAGE_TYPES = {
    ### DISCOVERY MSGS
    'PROBE': 'PROBE',
    'HEARTBEAT': 'HEARTBEAT',

    ### CLUSTER MEMBERSHIP MSGS
    'JOIN_REQUEST': 'JOIN_REQUEST',
    'JOIN_ACK': 'JOIN_ACK',
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
                self.set_timer('TIMER_EXPORT_CH_CSV', config.EXPORT_CH_CSV_INTERVAL)
                self.set_timer('TIMER_EXPORT_NEIGHBOR_CSV', config.EXPORT_NEIGHBOR_CSV_INTERVAL)

    ###################
    # CREATING DEFAULT PACKET STRUCTURE FOR INITIAL APPENDING
    # msg_type | dest_addr | next_hop | source_addr | TTL (hop count) | PAYLOAD 
    def create_pck(self, msg_type, dest, next_hop=None, source_addr=None, hop_count=None, unique_id=None):
        packet = {'msg_type': msg_type, 'dest': dest, 'next_hop': next_hop, 'source_addr': source_addr, 'hop_count': hop_count, 'unique_id': unique_id}
        return packet
    def send_probe(self): #probe to discover network
        self.send(self.create_pck(msg_type=MESSAGE_TYPES['PROBE'], dest=wsn.BROADCAST_ADDR, unique_id=self.id))
    def send_heartbeat(self): #periodic message and response to probes
        self.send({'dest': wsn.BROADCAST_ADDR,
            'msg_type': MESSAGE_TYPES['HEARTBEAT'],
            'source_addr': self.ch_addr if self.ch_addr is not None else self.addr,
            'unique_id': self.id,
            'role_type': self.role,
            'addr': self.addr,
            'ch_addr': self.ch_addr,
            'hop_count': self.hop_count})
    def send_join_request(self): #periodic message and response to probes
        self.send({'dest': wsn.BROADCAST_ADDR,
            'msg_type': MESSAGE_TYPES['HEARTBEAT'],
            'source_addr': self.ch_addr if self.ch_addr is not None else self.addr,
            'unique_id': self.id,
            'role_type': self.role,
            'addr': self.addr,
            'ch_addr': self.ch_addr,
            'hop_count': self.hop_count})
    ###################
    def on_receive(self, pck):
        if pck['msg_type'] == MESSAGE_TYPES['PROBE']: #so this should only be logic for nodes that can add them to the network
            unique_id = pck['unique_id']
            #if we havent heard from this node before, add to neighbor table
            if unique_id not in self.neighbors_table.keys():
                self.neighbors_table[unique_id] = pck
            self.log(unique_id)
            self.send_heartbeat()
            self.log(self.neighbors_table)
        if self.role == Roles.UNDISCOVERED:
            if pck['msg_type'] == MESSAGE_TYPES['HEARTBEAT']:
                #self.update_neighbor(pck)
                self.become_unregistered()



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
                    self.addr = wsn.Addr(self.id, 254)
                    self.ch_addr = wsn.Addr(self.id, 254)
                    self.set_timer('TIMER_HEARTBEAT', config.HEART_BEAT_TIME_INTERVAL)
                else:
                    #if we can't become root, try and try again!
                    self.c_probe = 0
                    self.set_timer('TIMER_PROBE', config.SLEEP_MODE_PROBE_TIME_INTERVAL)
        elif name == 'TIMER_HEARTBEAT':
            self.log("heartbeat sent")
            self.send_heartbeat()
            self.set_timer('TIMER_HEARTBEAT', config.HEART_BEAT_TIME_INTERVAL)









ROOT_ID = random.randint(0, config.SIM_NODE_COUNT)


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
