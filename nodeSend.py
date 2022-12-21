from copy import deepcopy
from datetime import datetime, timedelta
from threading import Event, Thread, Timer
import utils
import config

class NodeSend(Thread):
    def __init__(self, node):
        Thread.__init__(self)
        self.node = node
        self.client_sockets = [utils.create_client_socket() for i in range(config.numNodes)]
    
    def build_connection(self):
        for i in range(config.numNodes):
            self.client_sockets[i].connect(('localhost',config.port+i))
    
    def run(self):
        self._update()
    
    def _update(self):
        """Run Request-Enter-Exit circle
        Request: requests for entering the critical section either at the 
                 beginning or NEXT_REQ seconds after exiting the critical section.
        Enter: enters into the critical section when it receives enough 
               votes from the its voting set.
        Exit: exits the critical section after CS_INT seconds after entering
              the critical section.
        
        """
        while True:
            self.node.signal_request_cs.wait()
            self.node.request_cs(datetime.now())
            self.node.signal_enter_cs.wait()
            self.node.enter_cs(datetime.now())
            self.node.signal_exit_cs.wait()
            self.node.exit_cs(datetime.now())
    
    def send_message(self, msg, dest, multicast=False):
        if not multicast:
            self.node.lamport_ts += 1
            msg.set_ts(self.node.lamport_ts)
        assert dest == msg.dest
        self.client_sockets[dest].sendall(bytes(msg.to_json(),encoding='utf-8'))


    def multicast(self, msg, group):
        self.node.lamport_ts += 1
        msg.set_ts(self.node.lamport_ts)
        for dest in group:
            new_msg = deepcopy(msg)
            new_msg.set_dest(dest)
            assert new_msg.dest == dest
            assert new_msg.ts == msg.ts
            self.send_message(new_msg, dest, True)

