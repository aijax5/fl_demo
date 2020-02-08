 #utilities
import random
import time
import pickle
import codecs

#communication
from socketIO_client import SocketIO, LoggingNamespace

#training model
import tensorflow as tf
from tensorflow import keras

class LocalModel(object):
    def __init__(self, dataset):
        (x_train, y_train), (x_val, y_val) = dataset.load_data()
        
        def preprocess(x, y):
            x = tf.cast(x, tf.float32) / 255.0
            y = tf.cast(y, tf.int64)

            return x, y

        def create_dataset(xs, ys, n_classes=10):
            le=len(ys)
            ys = tf.one_hot(ys, depth=n_classes)
            return tf.data.Dataset.from_tensor_slices((xs, ys)) \
            .map(preprocess) \
            .shuffle(le) \
            .batch(128)
            
        self.train_dataset = create_dataset(x_train, y_train)
        self.val_dataset = create_dataset(x_val, y_val)
        
        self.model = keras.Sequential([
            keras.layers.Reshape(target_shape=(28 * 28,), input_shape=(28, 28)),
            keras.layers.Dense(units=256, activation='relu'),
            keras.layers.Dense(units=192, activation='relu'),
            keras.layers.Dense(units=128, activation='relu'),
            keras.layers.Dense(units=10, activation='softmax')
        ])
        
        self.model.compile(optimizer='adam', 
              loss=tf.losses.CategoricalCrossentropy(from_logits=True),
              metrics=['accuracy'])

        history = self.model.fit(
            self.train_dataset.repeat(), 
            epochs=2, 
            steps_per_epoch=500,
            validation_data=self.val_dataset.repeat(), 
            validation_steps=2
        )
        
        # return model    

     
    def trainOneEpoch(self):
        history = self.model.fit(
            self.train_dataset.repeat(), 
            epochs=1, 
            steps_per_epoch=500,
            validation_data=self.val_dataset.repeat(), 
            validation_steps=2
        )
    
    def getWeights(self):
        return self.model.get_weights()
    def setWeights(self,weights):
        return self.model.set_weights(weights)

class FederatedClient(object):

    def __init__(self, server_host, server_port,val):
       
        self.sio = SocketIO(server_host, server_port, LoggingNamespace)
        self.val=val
        self.register_handles()
        
        self.localModel = None
        
        self.sio.wait()

    def serilalizeObject(obj):
        return codecs.encode(pickle.dumps(obj), "base64").decode()
       

    def deserializeObject(s):
        return pickle.loads(codecs.decode(s.encode(), "base64"))
    
    def register_handles(self):
        ########## Socket IO messaging ##########
        def on_connect():
            print('connect')

        def on_disconnect():
            print('disconnect')

        def on_reconnect():
            print('reconnect')

        def on_client_update(*args):
            update = FederatedClient.deserializeObject(args[0])
            # update = args[0]
            self.localModel.setWeights(update)
            print("received avg as ",len(update))
            print("all good! training one more round!...")
            self.localModel.trainOneEpoch()
            print("\n\n sending in hot, new weights! ")
            # time.sleep(2)
            data = FederatedClient.serilalizeObject(self.localModel.getWeights())
            self.sio.emit('server_update', data)

        def on_init(data):
            print('lolli')
            print(data)
            self.localModel = LocalModel(keras.datasets.fashion_mnist)
            time.sleep(2)
            print("sending weights!!")
            dataString = FederatedClient.serilalizeObject(self.localModel.getWeights())
            self.sio.emit('server_update', dataString)
            
        def on_stop_and_eval(*args):
            req = args[0]
            self.sio.emit('client_eval', {'num':13})


        self.sio.on('connect', on_connect)
        self.sio.on('disconnect', on_disconnect)
        self.sio.on('reconnect', on_reconnect)
        self.sio.on('init', on_init)
        self.sio.on('client_update', on_client_update)
        self.sio.on('stop_and_eval', on_stop_and_eval)

if __name__ == "__main__":
    FederatedClient("127.0.0.1", 5000, {'num': 25})
