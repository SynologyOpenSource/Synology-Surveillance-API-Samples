import tensorflow as tf
import time

def setup_tf_conf():
    gpus = tf.config.list_physical_devices('GPU')
    if gpus:
        try:
            tf.config.experimental.set_virtual_device_configuration(
                gpus[0], [tf.config.experimental.VirtualDeviceConfiguration(memory_limit=1024)])
        except RuntimeError as e:
            print(e)

def get_latest_frame(q):
    while q.empty():
        time.sleep(0.01) # wait for a while for the next frame to be put into the queue

    while not q.empty():
        frame = q.get()

    return frame
