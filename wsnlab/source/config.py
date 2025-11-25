import math
import random
## network properties
BROADCAST_NET_ADDR = 255
BROADCAST_NODE_ADDR = 255
TOTAL_BITS = 16


## node properties
NODE_DEFAULT_TX_POWER = "0 dBm"
TX_POWER_LEVELS = ["-25 dBm", "-15 dBm", "-10 dBm", "-5 dBm", "0 dBm"]
NODE_TX_RANGES = {"-25 dBm": 5, "-15 dBm": 25, "-10 dBm": 50, "-5 dBm": 75, "0 dBm": 100} #TX range of nodes in meters
NODE_ARRIVAL_MAX = 200  # max time to wake up
NODE_LOSS_CHANCE = 0.05 #between 0 and 1
def get_tx_range(power):
    return NODE_TX_RANGES[power]
##Radio properties, CC2420
DATARATE = 250000 #data rate, 250kbps
MTU = 127 + 6 #size of the over the air packet
VOLTAGE = 3 #volts
TX_CURRENTS = {"-25 dBm": 8.5, "-15 dBm": 9.9, "-10 dBm": 11, "-5 dBm": 14, "0 dBm": 17.4} #mA
RX_CURRENT = 18.8 #mA
JOULES = 10.0
LOW_POWER_THRESHOLD = 0.2 #20% power we shut off
## simulation properties
SIM_NODE_COUNT = 100  # noce count in simulation
SIM_NODE_PLACING_CELL_SIZE = 75  # cell size to place one node
SIM_DURATION = 5000  # simulation Duration in seconds
SIM_TIME_SCALE = 0.01  #  The real time dureation of 1 second simualtion time
SIM_TERRAIN_SIZE = (1400, 1400)  #terrain size
SIM_TITLE = 'Data Collection Tree'  # title of visualization window
SIM_VISUALIZATION = True  # visualization active
SCALE = 1  # scale factor for visualization
VIS = 0 #0 for no viz, 1 for viz
SEED = 1 #seed for reproducibility 
random.seed(SEED)
NUM_OF_CHILDREN = 253 #num of children a given cluster head can have, must be 2^N - 3
bits_child = math.ceil(math.log2(NUM_OF_CHILDREN))
bits_cluster = TOTAL_BITS - bits_child
NUM_OF_CLUSTERS = (1 << bits_cluster) - 1
ALLOW_TX_POWER_CHOICE = 0 #1 for smart choice, 0 for default across all
TRANSMISSION_TIME = 0.00000005 #seconds, 133 * 8 / tx_rate = 4.256 ms round up to 5 ms
PROCESSING_TIME = 0.000001 #seconds, research for CC2420 was around a mean of 1 ms. HAD TO SCALE THESE VALUES DOWN FOR SAKE OF THE SIMULATION
## application properties
SLEEP_MODE_PROBE_TIME_INTERVAL = 30
HEART_BEAT_TIME_INTERVAL = 1
JOIN_REQUEST_TIME_INTERVAL = 10
JR_THRESHOLD_TO_EXPAND_TX_RANGE = 10
NETWORK_REQUEST_TIME_INTERVAL = JOIN_REQUEST_TIME_INTERVAL * 2
DATA_INTERVAL = 100
MESH_HOP_N = 5
TABLE_SHARE_INTERVAL = 30
REPAIRING_METHOD = 'FIND_ANOTHER_PARENT' # 'ALL_ORPHAN', 'FIND_ANOTHER_PARENT'
EXPORT_CH_CSV_INTERVAL = 10  # simulation time units;
EXPORT_NEIGHBOR_CSV_INTERVAL = 10  # simulation time units;

#PARAMETERS TO KILL NODES
node_ids = [] #25 is a good one to kill
def generate_sleep_cycles(node_ids, min_death, max_death, min_wakeup_delay, max_wakeup_delay):
    cycles = {}

    for nid in node_ids:
        death = random.uniform(min_death, max_death)

        # wakeup must be after death
        wakeup_delay = random.uniform(min_wakeup_delay, max_wakeup_delay)
        wakeup = death + wakeup_delay

        cycles[nid] = {
            "death_time": death,
            "wakeup_time": wakeup
        }

    return cycles
MIN_DEATH = NODE_ARRIVAL_MAX
MAX_DEATH = MIN_DEATH * 3
MIN_WAKEUP = MAX_DEATH + 1
MAX_WAKEUP = MIN_WAKEUP + NODE_ARRIVAL_MAX
KILL_AND_WAKEUP = generate_sleep_cycles(node_ids, MIN_DEATH, MAX_DEATH, MIN_WAKEUP, MAX_WAKEUP)