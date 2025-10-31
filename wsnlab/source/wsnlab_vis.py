"""Visualisation of wsnlab library. Based on wsnsimpy_tk. Used package instead of message by Mustafa Tosun.
"""
from source import wsnlab
from source.wsnlab import *
from threading import Thread
from topovis import Scene
from topovis.TkPlotter import Plotter


class Node(wsnlab.Node):
    """Class to model a visualised network node inherited wsnlab.Node.

       Attributes:
           scene (Scene): Scene object to visualise

    """

    ###################
    def __init__(self, sim, id, pos):
        """Constructor for visualised Node class. Creates a node in topovis scene.

           Args:
               sim (Simulator): Simulation environment of node.
               id (int): Global unique ID of node.
               pos (Tuple(double,double)): Position of node.

           Returns:
               Node: Created node object.
        """
        super().__init__(sim, id, pos)
        self.scene = self.sim.scene
        self.scene.node(id, *pos)

    ###################
    def send(self, pck):
        """Visualise sending process in addition to base send method.

           Args:
               pck (Dict): Package to be sent.

           Returns:

        """
        # UNcomment for Radio Circles 

        #obj_id = self.scene.circle(
        #    self.pos[0], self.pos[1],
        #    self.tx_range,
        #    line="wsnsimpy:tx")
        
        super().send(pck)
        
        #Uncomment for Radio Circles 
        #self.delayed_exec(0.2, self.scene.delshape, obj_id)
        
        # When unicast is added, it needs to be re-arranged
        if not pck['dest'].is_equal(wsnlab.BROADCAST_ADDR):
            print(pck)
            if 'next_hop' in pck.keys():
                addr = pck['next_hop'].node_addr
                if addr == 254:
                    addr = pck['next_hop'].net_addr
                src_x, src_y = self.pos
                dest_x, dest_y = self.sim.nodes[addr].pos

                # Draw the line (path)
                #line_id = self.scene.line(
                #    src_x, src_y,
                #    dest_x, dest_y,
                #    line="wsnsimpy:unicast"
                #)

                # Animate a moving dot (packet)
                steps = 25
                for i in range(steps + 1):
                    t = i / steps
                    dot_x = src_x + (dest_x - src_x) * t
                    dot_y = src_y + (dest_y - src_y) * t

                    # create + schedule deletion of each circle
                    dot_id = self.scene.circle(dot_x, dot_y, 1, line="wsnsimpy:packet")
                    self.delayed_exec(0.02 * (i + 1), self.scene.delshape, dot_id)               
            else:
                addr = pck['dest'].node_addr
                if addr == 254:
                    addr = pck['dest'].net_addr             
                src_x, src_y = self.pos
                dest_x, dest_y = self.sim.nodes[addr].pos

                # Draw the line (path)
                #line_id = self.scene.line(
                #    src_x, src_y,
                #    dest_x, dest_y,
                #    line="wsnsimpy:unicast"
                #)

                # Animate a moving dot (packet)
                steps = 25
                for i in range(steps + 1):
                    t = i / steps
                    dot_x = src_x + (dest_x - src_x) * t
                    dot_y = src_y + (dest_y - src_y) * t

                    # create + schedule deletion of each circle
                    dot_id = self.scene.circle(dot_x, dot_y, 1, line="wsnsimpy:packet")
                    self.delayed_exec(0.02 * (i + 1), self.scene.delshape, dot_id)

                # Remove the line after a short delay
                #self.delayed_exec(0.25, self.scene.delshape, line_id)



    ###################


    def draw_tx_range(self):
        """Draws transmission range of the node.

           Args:

           Returns:

        """
        obj_id =self.scene.circle(self.pos[0], self.pos[1], self.tx_range, line="wsnsimpy:tx")
        #self.delayed_exec(0.2, self.scene.delshape, obj_id)



    def move(self, x, y):
        """Visualise move process in addition to base move method.

           Args:
               x (double): x of position.
               y (double): y of position.

           Returns:

        """
        super().move(x, y)
        self.scene.nodemove(self.id, x, y)

    ####################
    def draw_parent(self):
        """Draws parent relation to given destination address.

           Args:

           Returns:

        """
        self.scene.addlink(self.parent_gui, self.id, "parent")

    ####################
    def erase_parent(self):
        """Draws parent relation to given destination address.

           Args:

           Returns:

        """
        if self.parent_gui is not None:
            self.scene.dellink(self.parent_gui, self.id, "parent")


###########################################################
class _FakeScene:
    def _fake_method(self, *args, **kwargs):
        pass

    def __getattr__(self, name):
        return self._fake_method


###########################################################


###########################################################
class Simulator(wsnlab.Simulator):
    '''Wrap WsnSimPy's Simulator class so that Tk main loop can be started in the
    main thread

    Attributes:
        visual (bool): A flag to visualising process.
        terrain_size (Tuple(double,double)): Size of visualised terrain.
    '''

    def __init__(self, duration, timescale=1, seed=0, terrain_size=(1000, 1000), visual=True, title=None):
        """Constructor for visualised Simulator class.

           Args:
               duration (double): Duration of simulation.
               timescale (double): Seconds in real time for 1 second in simulation. It arranges speed of simulation
               seed (double): seed for Random bbject.
               terrain_size (Tuple(double,double)): Size of visualised terrain.
               visual (bool): A flag to visualising process.
               title (string): Title of scene.

           Returns:
               Simulator: Created Simulator object.
        """
        super().__init__(duration, timescale, seed)
        self.visual = visual
        self.terrain_size = terrain_size
        if self.visual:
            self.scene = Scene(realtime=True)
            self.scene.linestyle("wsnsimpy:tx", color=(0, 0, 1), dash=(5, 5))
            self.scene.linestyle("wsnsimpy:ack", color=(0, 1, 1), dash=(5, 5))
            self.scene.linestyle("wsnsimpy:unicast", color=(0, 0, 1), width=3, arrow='head')
            self.scene.linestyle("wsnsimpy:packet", color=(1, 0, 0), width=3)
            self.scene.linestyle("wsnsimpy:collision", color=(1, 0, 0), width=3)
            self.scene.linestyle("parent", color=(0,.8,0), arrow="tail", width=2)
            if title is None:
                title = "WsnSimPy"
            self.tkplot = Plotter(windowTitle=title, terrain_size=terrain_size)
            self.tk = self.tkplot.tk
            self.scene.addPlotter(self.tkplot)
            self.scene.init(*terrain_size)
        else:
            self.scene = _FakeScene()

    def _update_time(self):
        """Updates time in scene.

           Args:

           Returns:
        """
        while True:
            self.scene.setTime(self.now)
            yield self.timeout(0.1)

    def run(self):
        """Starts visualisation process. Puts base run method to a Thread so that visualisation become main process.

           Args:

           Returns:
        """
        if self.visual:
            self.env.process(self._update_time())
            thr = Thread(target=super().run)
            thr.setDaemon(True)
            thr.start()
            self.tkplot.tk.mainloop()
        else:
            super().run()
