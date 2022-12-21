import select
from threading import Thread
import utils
from message import Message
import json
from enum_type import MSG_TYPE, STATE
import heapq


class NodeServer(Thread):
    def __init__(self, node):
        Thread.__init__(self)
        self.node = node
    
    def run(self):
        self.update()

    def update(self):
        self.connection_list = []
        self.server_socket = utils.create_server_socket(self.node.port)
        self.connection_list.append(self.server_socket)

        while self.node.daemon:
            (read_sockets, write_sockets, error_sockets) = select.select(
                self.connection_list, [], [], 5)
            if not (read_sockets or write_sockets or error_sockets):
                print('NS%i - Timed out'%self.node.id) #force to assert the while condition 
            else:
                for read_socket in read_sockets:
                    if read_socket == self.server_socket:
                        (conn, addr) = read_socket.accept()
                        self.connection_list.append(conn)
                    else:
                        try:
                            msg_stream = read_socket.recvfrom(4096)
                            for msg in msg_stream:
                                try:
                                    ms = json.loads(str(msg,"utf-8"))
                                    self.process_message(ms)
                                except:
                                    None
                        except:
                            read_socket.close()
                            self.connection_list.remove(read_socket)
                            continue
        
        self.server_socket.close()

    # Función que gestiona la llegada de un mensaje según su tipo
    def process_message(self, msg):
        # print("Node_%i receive msg: %s"%(self.node.id,msg))
        self.node.lamport_ts = max(self.node.lamport_ts + 1, msg['ts'])
        # Dependiendo del tipo de mensaje recibido, lleva a cabo distintas acciones
        if msg['msg_type'] == MSG_TYPE.REQUEST:
            self._on_request(msg)
        elif msg['msg_type'] == MSG_TYPE.GRANT:
            self._on_grant(msg)
        elif msg['msg_type'] == MSG_TYPE.RELEASE:
            self._on_release(msg)
        elif msg['msg_type'] == MSG_TYPE.FAIL:
            self._on_fail(msg)
        elif msg['msg_type'] == MSG_TYPE.INQUIRE:
            self._on_inquire(msg)
        elif msg['msg_type'] == MSG_TYPE.YIELD:
            self._on_yield(msg)

    def _on_request(self, request_msg):
        """Handle REQUEST type message
        a. Cache the request if the node is in the critical section currently.
        b. Otherwise, check if the node has voted for a request or not.
                i. If it has, either send an INQUIRE message to the previous 
                   voted requesting node or send a FAIL message to the current 
                   requesting node. (depending on the timestamp and node id order 
                   of the requests)
                ii. Otherwise, vote for current request directly.
        Args:
            request_msg (Message): REQUEST type message object
        """
        print("Node_%i received a request msg from Node_%i"%(self.node.id, request_msg['src']))
        if self.node.mystate == STATE.HELD:
            heapq.heappush(self.node.request_queue, request_msg)
        else:
            if self.node.has_voted:
                heapq.heappush(self.node.request_queue, request_msg)
                response_msg = Message(src=self.node.id)
                if (request_msg < self.node.voted_request and 
                        not self.node.has_inquired):
                    response_msg.set_type(MSG_TYPE.INQUIRE)
                    response_msg.set_dest(self.node.voted_request['src'])
                    self.node.has_inquired = True
                else:
                    response_msg.set_type(MSG_TYPE.FAIL)
                    response_msg.set_dest(request_msg['src'])
                self.node.client.send_message(response_msg, response_msg.dest)
            else:
                self._grant_request(request_msg)

    def _on_release(self, release_msg=None):
        """Handle RELEASE type message
        a. If request priority queue is not empty, pop out the request with
           the highest priority and handle that request.
        b. Otherwise, reset corresponding flags.
        Args:
            release_msg (Message): RELEASE type message object
        """
        self.node.has_inquired = False
        if self.node.request_queue:
            next_request = heapq.heappop(self.node.request_queue)
            self._grant_request(next_request)
        else:
            self.node.has_voted = False
            self.node.voted_request = None

    def _grant_request(self, request_msg):
        """Vote for a request
        Args:
            request_msg (Message): REQUEST type message object
        """
        print("Node_%i granting access to CS to Node_%i"%(self.node.id, request_msg['src']))
        grant_msg = Message(msg_type=MSG_TYPE.GRANT,
                            src=self.node.id,
                            dest=request_msg['src'],
                            )
        self.node.client.send_message(grant_msg, grant_msg.dest)
        self.node.has_voted = True
        self.node.voted_request = request_msg

    def _on_grant(self, grant_msg):
        """Handle GRANT type message
        Increase the counter of received votes.
        Args:
            grant_msg (Message): GRANT type message object
            
        """
        # self._node.voting_set[grant_msg.src] = grant_msg
        self.node.num_votes_received += 1
        print("Node_%i received a grant msg from Node_%i. Number of votes received: %i"%(self.node.id, grant_msg['src'], self.node.num_votes_received))

    def _on_fail(self, fail_msg):
        """Handle FAIL type message
        Args:
            fail_msg (Message): FAIL type message object
            
        """
        # self._node.voting_set[fail_msg.src] = fail_msg
        pass

    def _on_inquire(self, inquire_msg):
        """Handle INQUIRE type message
        If current node is not in the critical section, send a 
        YIELD message to the inquiring node, indicating it
        would like the inquiring node to revoke the vote.
        Args:
            inquire_msg (Message): INQUIRE type message object
            
        """
        print("Node_%i received an inquire msg"%self.node.id)
        if self.node.mystate != STATE.HELD:
            # self._node.voting_set[inquire_msg.src] = None
            self.node.num_votes_received -= 1
            yield_msg = Message(msg_type=MSG_TYPE.YIELD,
                                src=self.node.node.id,
                                dest=inquire_msg['src'])
            self.node.client.send_message(yield_msg, yield_msg.dest)

    def _on_yield(self, yield_msg):
        """Handle YIELD type message
        Put the latest voted request back to request queue.
        Then behaves just like receiving a RELEASE message.
        Args:
            yield_msg (Message): YIELD type message object
            
        """
        print("Node_%i received a yield msg"%self.node.id)
        heapq.heappush(self.node.request_queue,
                       self.node.voted_request)
        self._on_release()

 