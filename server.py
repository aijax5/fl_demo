#utilities
import random
import sys
import time
import threading
import pickle
import codecs
import numpy as np

#communication
from flask import *
from flask_socketio import SocketIO
from flask_socketio import *
import gevent
from flask import copy_current_request_context


class FedNetServer(object):

    def __init__(self, host, port):
        self.ready_client_sids = set()

        self.app = Flask(__name__)
        self.socketio = SocketIO(self.app)
        self.host = host
        self.port = port
        
        
        self.flag=True
        self.getCount=True
        self.tempCount=0
        self.clientCounter=0
        self.tempSum=0
        self.val={'num':0}
        self.client_weights=[]
        #####
     
        # socket io messages
        self.register_handles()


        @self.app.route('/')
        def dashboard():
            return render_template('./index.html')

        def trun(self):
            with self.app.test_request_context(): 
                time.sleep(10) 
                print("sending broadcast to all clients ")
                emit('init',broadcast = True, namespace='/') 
       
        if self.flag:
            t1 = threading.Thread(target=trun, args=(self,)) 
            print("in thread")
            t1.start()
            self.flag=False

    def serilalizeObject(obj):
        return codecs.encode(pickle.dumps(obj), "base64").decode()
       

    def deserializeObject(s):
        return pickle.loads(codecs.decode(s.encode(), "base64"))
    def getAverages(self,client_weights):
            new=[]
            for i,weights in enumerate(client_weights):
                if i == 0:
                    new = weights
                else:
                    for j,weight in enumerate(weights):
                        new[j] += weight
            
            for k,w in enumerate(new):
                new[k] = np.divide(w,float(len(client_weights)))
            print( "avg i=2,0 ",new[2][0])
            return new
           
    def register_handles(self):
        # single-threaded async, no need to lock

        @self.socketio.on('connect')
        def handle_connect():
            print(request.sid, "connected")
            self.clientCounter=self.clientCounter + 1
            

        @self.socketio.on('reconnect')
        def handle_reconnect():
            print(request.sid, "reconnected")
            self.clientCounter=self.clientCounter + 1

        @self.socketio.on('disconnect')
        def handle_disconnect():
            print(request.sid, "disconnected")
            self.clientCounter=self.clientCounter - 1


        @self.socketio.on('client_wake_up')
        def handle_wake_up():
            print("client wake_up: ", request.sid)
      
        @self.socketio.on('client_ready')
        def handle_client_ready(data):
            print("client ready ", self.clientCounter, data)
      
        

        @self.socketio.on('server_update')
        def handle_client_update(data):
            if self.getCount:
                self.tempCount=self.clientCounter
                self.getCount=False
                

            self.tempCount -= 1
            data = FedNetServer.deserializeObject(data)
            self.client_weights.append(data)
            print("weights received ",len(self.client_weights))

            if self.tempCount == 0:
                self.new_weights = self.getAverages(self.client_weights)
                self.client_weights.clear()
                time.sleep(3)
                self.client_weights.clear()
                print('null and void ',len(self.client_weights))
                data=FedNetServer.serilalizeObject(self.new_weights)
                self.getCount=True
                emit('client_update',data,broadcast = True, namespace='/')
                
            
    def start(self):
        self.socketio.run(self.app, host=self.host, port=self.port)


if __name__ == '__main__':
    
    server = FedNetServer("127.0.0.1", 5000)
    print("listening on 127.0.0.1 : 5000")
    server.start()
