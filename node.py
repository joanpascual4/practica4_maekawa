from threading import Event, Thread, Timer
from datetime import datetime, timedelta
from nodeServer import NodeServer
from nodeSend import NodeSend
from message import Message
import config
from enum_type import MSG_TYPE, STATE
from math import ceil, sqrt
from random import randint

class Node():
    def __init__(self,id):
        Thread.__init__(self)
        self.id = id
        self.mystate = STATE.INIT
        self.port = config.port+id
        self.daemon = True
        self.lamport_ts = 0

        # Attributes as a voter (receive & process request)
        self.has_voted = False
        self.voted_request = None
        self.request_queue = []  # a priority queue (key = lamportTS, value = request)

        # Creación del grupo de votación (para 3 nodos)
        #if self.id == 0: 
        #    self.voting_set = (0, 1)
        #elif self.id == 1:
        #    self.voting_set = (1, 2)
        #elif self.id == 2:
        #    self.voting_set = (0, 2)

        # Creación del grupo de votación (para 7 nodos)
        if self.id == 0: 
            self.voting_set = (0, 1, 2)
        elif self.id == 1:
            self.voting_set = (1, 3, 5)
        elif self.id == 2:
            self.voting_set = (2, 4, 5)
        elif self.id == 3:
            self.voting_set = (0, 3, 4)
        elif self.id == 4:
            self.voting_set = (1, 4, 6)
        elif self.id == 5:
            self.voting_set = (0, 5, 6)
        elif self.id == 6:
            self.voting_set = (2, 3, 6)

        # Attributes as a proposer (propose & send request)
        self.num_votes_received = 0
        self.has_inquired = False

        self.server = NodeServer(self)
        self.server.start()

        self.client = NodeSend(self)
        
        # Event signals
        self.signal_request_cs = Event()
        self.signal_request_cs.set() # INICIALMENTE QUIERE ENTRAR A LA SECCIÓN CRÍTICA
        self.signal_enter_cs = Event()
        self.signal_exit_cs = Event()

        # Timestamp for next expected request/exit
        self.time_request_cs = None
        self.time_exit_cs = None

    # Función lanzada por el evento signal_request_cs
    # Cambia el estado a REQUEST y envía el mensaje a su grupo de votantes
    def request_cs(self, ts):
        self.mystate = STATE.REQUEST
        self.lamport_ts += 1
        print("Node %i requesting CS"%self.id)
        request_msg = Message(msg_type=MSG_TYPE.REQUEST,
                              src=self.id,
                              data = "Request CS")
        self.client.multicast(request_msg, self.voting_set)
        self.signal_request_cs.clear()

    # Función lanzada por el evento signal_enter_cs
    # Ddefine el tiempo que estará en la SC y cambia el estado a HELD
    def enter_cs(self, ts):
        self.time_exit_cs = ts + timedelta(milliseconds=randint(5, 10)) # Tiempo aleatorio
        self.mystate = STATE.HELD
        self.lamport_ts += 1
        print("Node %i accessing CS"%self.id)
        self.signal_enter_cs.clear()

    # Función lanzada por el evento signal_exit_cs
    # Ddefine el tiempo hasta el próximo request y cambia su estado a RELEASE
    # También notifica a su grupo de votantes que ha salido de la SC
    def exit_cs(self, ts):
        self.time_request_cs = ts + timedelta(milliseconds=randint(10, 20)) # Tiempo aleatorio
        self.mystate = STATE.RELEASE
        self.lamport_ts += 1
        self.num_votes_received = 0 # Reinicia los votos recibidos
        print("Node %i leaving CS"%self.id)
        release_msg = Message(msg_type=MSG_TYPE.RELEASE,
                              src=self.id,
                              data = "Leaving CS")
        self.client.multicast(release_msg, self.voting_set)
        self.signal_exit_cs.clear()


    def do_connections(self):
        self.client.build_connection()

    def state(self):
        timer = Timer(1, self.state) #Each 1s the function call itself
        timer.start()
        self.curr_time = datetime.now()
        # Comprueba el estado del nodo
        if (self.mystate == STATE.RELEASE and self.time_request_cs <= self.curr_time):
            if not self.signal_request_cs.is_set():
                self.signal_request_cs.set() # Hace un Request a sus vecinos para entrar en la SC
        elif (self.mystate == STATE.REQUEST and self.num_votes_received == len(self.voting_set)):
            if not self.signal_enter_cs.is_set():
                self.signal_enter_cs.set() # Entra a la SC
        elif (self.mystate == STATE.HELD and self.time_exit_cs <= self.curr_time):
            if not self.signal_exit_cs.is_set():
                self.signal_exit_cs.set() # Sale de la SC

        self.wakeupcounter += 1

        # PARA QUE LA EJECUCIÓN SE DETENGA, DESCOMENTAR EL SIGUIENTE CÓDIGO
        # INDICAR LAS VECES QUE SE QUIERE INVOCAR LA FUNCIÓN STATE
        #if self.wakeupcounter == 10: # Por defecto se levanta 10 veces
        #    timer.cancel()
        #    print("Stopping N%i"%self.id)
        #    self.daemon = False

    def run(self):
        print("Run Node%i with the follows %s"%(self.id,self.voting_set))
        self.client.start()
        self.wakeupcounter = 0
        self.state()

