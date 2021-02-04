import sys
sys.path.append('../')
sys.path.append('../TensorFlow-2.x-YOLOv3')

from yolov3.configs import *
from yolov3.utils import load_yolo_weights, image_preprocess, postprocess_boxes, nms, draw_bbox, read_class_names
from yolov3.yolov4 import Create_Yolo
import tensorflow as tf
import numpy as np
import os
from webAPI import WebAPI
import cv2
import time
import threading
import queue

os.environ['CUDA_VISIBLE_DEVICES'] = '0'

from utils import setup_tf_conf, get_latest_frame
setup_tf_conf()

# replace the following with your NVR IP address and port and user account
IP_ADDR = 'xxx.xxx.xxx.xxx'
PORT = 'xxxx'
ACCOUNT = 'xxxxxx'
PASSWORD = 'xxxxxx'


def check_fall(NUM_CLASS, class_ind, w, h):
    return NUM_CLASS[class_ind] == 'person' and w > 1.8 * h


def detect_fall(YoloV3, img, input_size=416, CLASSES=YOLO_COCO_CLASSES, score_threshold=0.3, iou_threshold=0.45, rectangle_colors=''):
    try:
        original_image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        original_image = cv2.cvtColor(original_image, cv2.COLOR_BGR2RGB)
    except:
        raise('Invalid image!')

    image_data = image_preprocess(np.copy(original_image), [
                                  input_size, input_size])
    image_data = tf.expand_dims(image_data, 0)

    t1 = time.time()
    pred_bbox = YoloV3.predict(image_data)
    t2 = time.time()

    pred_bbox = [tf.reshape(x, (-1, tf.shape(x)[-1])) for x in pred_bbox]
    pred_bbox = tf.concat(pred_bbox, axis=0)

    bboxes = postprocess_boxes(
        pred_bbox, original_image, input_size, score_threshold)
    bboxes = nms(bboxes, iou_threshold, method='nms')

    ms = (t2 - t1) * 1000
    fps = 1000 / ms

    print('Time: {:.2f}ms, {:.1f} FPS'.format(ms, fps))

    fall_bboxes = []
    for i, bbox in enumerate(bboxes):
        coor = np.array(bbox[:4], dtype=np.int32)
        class_ind = int(bbox[5])
        (x1, y1), (x2, y2) = (coor[0], coor[1]), (coor[2], coor[3])

        if check_fall(CLASSES, class_ind, x2-x1, y2-y1):
            fall_bboxes.append(bbox)

    if len(fall_bboxes) > 0:
        image = draw_bbox(original_image, fall_bboxes,
                          rectangle_colors=rectangle_colors)
        cv2.imwrite('fall-detection.jpg', image)
        return True
    else:
        return False


def read_frame(q, rtsp):
    stream = cv2.VideoCapture(rtsp)

    while True:
        ret, frame = stream.read()

        if ret:
            q.put(frame)


def process_frame(q, webapi, camera_id, yolo, classes, fall_label):
    while True:
        frame = get_latest_frame(q)

        if detect_fall(yolo, frame, input_size=YOLO_INPUT_SIZE, CLASSES=classes, rectangle_colors=(255, 0, 0)):
            print('Fall detect!')
            webapi.start_action_rule_recording()
            webapi.send_notification()

            # Wait for the Action Rule recording finishing starting
            # If there's no sleep here, tags might be added to the prevous recording.
            time.sleep(1)

            recordings = webapi.list_recordings([camera_id])
            recording_ids = [recording['id'] for recording in recordings]

            recording_id = recording_ids[0]
            webapi.add_label_to_recording(recording_id, fall_label)



def main():
    webapi = WebAPI(IP_ADDR, PORT, ACCOUNT, PASSWORD)

    cameras = webapi.list_cameras()
    camera_ids = [camera['id'] for camera in cameras]

    # the last added camera in the Surveillance Station
    camera_id = camera_ids[-1]
    rtsp = webapi.get_liveview_rtsp(camera_id)

    fall_label = webapi.create_recording_label('fall_event')

    # Initialize fall detection model
    yolo = Create_Yolo(input_size=YOLO_INPUT_SIZE)
    load_yolo_weights(yolo, YOLO_V3_WEIGHTS)  # use Darknet weights
    classes = read_class_names(YOLO_COCO_CLASSES)

    q = queue.Queue()

    p1 = threading.Thread(target=read_frame, args=([q, rtsp]))
    p2 = threading.Thread(target=process_frame,
                          args=([q, webapi, camera_id, yolo, classes, fall_label]))
    p1.start()
    p2.start()

    p1.join()
    p2.join()

    webapi.logout()


if __name__ == '__main__':
    main()
