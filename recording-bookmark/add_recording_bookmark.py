import sys
sys.path.append('../')
sys.path.append('../TensorFlow-2.x-YOLOv3')
sys.path.append('../mmfashion')

import os
import cv2
import numpy as np
import tensorflow as tf
import torch
from yolov3.utils import load_yolo_weights, image_preprocess, postprocess_boxes, nms, draw_bbox, read_class_names
from deep_sort import generate_detections as gdet
from deep_sort.tracker import Tracker
from deep_sort.detection import Detection
from deep_sort import nn_matching
from yolov3.configs import *
import time
from yolov3.yolov4 import Create_Yolo

os.environ['CUDA_VISIBLE_DEVICES'] = '0'
from utils import setup_tf_conf, get_latest_frame
setup_tf_conf()


from mmcv import Config
from mmcv.runner import load_checkpoint
from mmfashion.core import AttrPredictor, CatePredictor
from mmfashion.models import build_predictor
from mmfashion.utils import get_img_tensor_from_cv2, get_imgs_tensor_from_cv2

from webAPI import WebAPI
import queue
import threading
from collections import Counter

# replace the following with your NVR and user account
IP_ADDR = 'xxx.xxx.xxx.xxx'
PORT = 'xxxx'
ACCOUNT = 'xxxxxx'
PASSWORD = 'xxxxxx'

RECORDINGS_DIRECTORY = 'recordings'
CHECKPOINT_FILE = '../mmfashion/checkpoint/CateAttrPredict/vgg/global/latest.pth'
CONFIG_FILE = '../mmfashion/configs/category_attribute_predict/global_predictor_vgg.py'
DEEP_SORT_MODEL_FILE = '../TensorFlow-2.x-YOLOv3/model_data/mars-small128.pb'
USE_CUDA = True

if YOLO_TYPE == "yolov4":
    Darknet_weights = YOLO_V4_TINY_WEIGHTS if TRAIN_YOLO_TINY else YOLO_V4_WEIGHTS
if YOLO_TYPE == "yolov3":
    Darknet_weights = YOLO_V3_TINY_WEIGHTS if TRAIN_YOLO_TINY else YOLO_V3_WEIGHTS

def category_classifier(model, cate_predictor, track, part, landmark_tensor):
    if part == 'upper':
        samples = track.upper_samples
    elif part == 'lower':
        samples = track.lower_samples
    else:
        raise NameError('Invalid part of body!')

    if len(samples) == 0:
        return 'Unrecognizable'

    imgs_tensor = get_imgs_tensor_from_cv2(samples, True)
    attr_prob, cate_prob = model(imgs_tensor, attr=None,
                                 landmark=landmark_tensor, return_loss=False)
    results, confidences = cate_predictor.get_prediction_from_samples(
        cate_prob, 5)
    cate_predictor.show_prediction(cate_prob)

    counter = Counter([r[0] for r in results])
    votes = counter.most_common()

    if len(results) < 1:
        result = 'Unrecognizable'
    else:
        result = votes[0][0]

    return result


def categories_classifier(model, cate_predictor, track, landmark_tensor):
    upper_result = category_classifier(
        model, cate_predictor, track, 'upper', landmark_tensor)
    lower_result = category_classifier(
        model, cate_predictor, track, 'lower', landmark_tensor)

    if upper_result != 'Unrecognizable' and lower_result != 'Unrecognizable':
        result = '{} {}'.format(upper_result, lower_result)
    elif upper_result != 'Unrecognizable' and lower_result == 'Unrecognizable':
        result = upper_result
    elif upper_result == 'Unrecognizable' and lower_result != 'Unrecognizable':
        result = lower_result
    else:
        result = 'Unrecognizable'

    return result


def predict_tracks_cate(model, cate_predictor, tracks, landmark_tensor, video_path):
    marks = []

    for track in tracks:
        result = categories_classifier(
            model, cate_predictor, track, landmark_tensor)

        sec_since_start = int(track.msec_since_start // 1000)
        sec_since_start = sec_since_start if sec_since_start != 0 else 1

        marks.append([sec_since_start, result])

    return marks


def add_text_to_bookmarks(bookmarks, marks):
    for sec_since_start, text in marks:
        if sec_since_start in bookmarks:
            bookmarks[sec_since_start].append(text)
        else:
            bookmarks[sec_since_start] = [text]


def Object_tracking(YoloV3, webapi, recording_id, video_path, model, cate_predictor, landmark_tensor, input_size=416, CLASSES=YOLO_COCO_CLASSES, score_threshold=0.3, iou_threshold=0.45, rectangle_colors='', Track_only=[]):
    # Definition of the parameters
    max_cosine_distance = 0.7
    nn_budget = None

    # initialize deep sort object
    encoder = gdet.create_box_encoder(DEEP_SORT_MODEL_FILE, batch_size=1)
    metric = nn_matching.NearestNeighborDistanceMetric(
        "cosine", max_cosine_distance, nn_budget)
    tracker = Tracker(metric)

    times = []

    if video_path:
        vid = cv2.VideoCapture(video_path)  # detect on video
    else:
        vid = cv2.VideoCapture(0)  # detect from webcam

    # by default VideoCapture returns float instead of int
    width = int(vid.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(vid.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(vid.get(cv2.CAP_PROP_FPS))

    NUM_CLASS = read_class_names(CLASSES)
    key_list = list(NUM_CLASS.keys())
    val_list = list(NUM_CLASS.values())

    bookmarks = {}

    while True:
        _, img = vid.read()
        print(vid.get(cv2.CAP_PROP_POS_MSEC))

        try:
            original_image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            original_image = cv2.cvtColor(original_image, cv2.COLOR_BGR2RGB)
        except:
            break

        image_data = image_preprocess(np.copy(original_image), [
                                      input_size, input_size])
        image_data = tf.expand_dims(image_data, 0)

        t1 = time.time()
        pred_bbox = YoloV3.predict(image_data)
        t2 = time.time()

        times.append(t2 - t1)
        times = times[-20:]

        pred_bbox = [tf.reshape(x, (-1, tf.shape(x)[-1])) for x in pred_bbox]
        pred_bbox = tf.concat(pred_bbox, axis=0)

        bboxes = postprocess_boxes(
            pred_bbox, original_image, input_size, score_threshold)
        bboxes = nms(bboxes, iou_threshold, method='nms')

        # extract bboxes to boxes (x, y, width, height), scores and names
        boxes, scores, names = [], [], []
        for bbox in bboxes:
            if len(Track_only) != 0 and NUM_CLASS[int(bbox[5])] in Track_only or len(Track_only) == 0:
                boxes.append([bbox[0].astype(int), bbox[1].astype(int), bbox[2].astype(
                    int)-bbox[0].astype(int), bbox[3].astype(int)-bbox[1].astype(int)])
                scores.append(bbox[4])
                names.append(NUM_CLASS[int(bbox[5])])

        # Obtain all the detections for the given frame.
        boxes = np.array(boxes)
        names = np.array(names)
        scores = np.array(scores)
        features = np.array(encoder(original_image, boxes))
        detections = [Detection(bbox, score, class_name, feature) for bbox,
                      score, class_name, feature in zip(boxes, scores, names, features)]

        # Pass detections to the deepsort object and obtain the track information.
        tracker.predict()
        deleted_tracks = tracker.update(detections, vid.get(
            cv2.CAP_PROP_POS_MSEC), original_image)

        # Throw frames into classifier once a person is deleted from the tracker
        marks = predict_tracks_cate(
            model, cate_predictor, deleted_tracks, landmark_tensor, video_path)
        add_text_to_bookmarks(bookmarks, marks)

        ms = sum(times)/len(times)*1000
        fps = 1000 / ms

        print("Time: {:.2f}ms, {:.1f} FPS".format(ms, fps))

    marks = predict_tracks_cate(
        model, cate_predictor, tracker.tracks, landmark_tensor, video_path)
    add_text_to_bookmarks(bookmarks, marks)

    timestamp = int(os.path.splitext(video_path)[0].split('-')[-1])
    for sec_since_start, texts in bookmarks.items():
        webapi.add_bookmark(recording_id, ' | '.join(
            texts), '', timestamp + sec_since_start)


def download_recordings(q, webapi):
    cameras = webapi.list_cameras()
    camera_ids = [camera['id'] for camera in cameras]

    if len(camera_ids) > 0:
        pass
    else:
        q.put((-1, 'Error'))
        raise NameError('There is no camera in the Serveillance Station!')

    recordings = webapi.list_recordings()
    recording_ids = [recording['id'] for recording in recordings]
    recording_ids = recording_ids[1:]  # skip the current recording

    if not os.path.exists(RECORDINGS_DIRECTORY):
        os.mkdir(RECORDINGS_DIRECTORY)

    for recording_id in recording_ids:
        recording_filename = webapi.download_recording(
            recording_id, RECORDINGS_DIRECTORY)
        q.put((recording_id, recording_filename))

    q.put((-1, 'Done'))


def process_recordings(q, webapi):
    # Initialize clothe category classifier
    cfg = Config.fromfile(CONFIG_FILE)

    landmark_tensor = torch.zeros(8)

    model = build_predictor(cfg.model)
    load_checkpoint(model, CHECKPOINT_FILE, map_location='cpu')
    print('model loaded from {}'.format(CHECKPOINT_FILE))
    if USE_CUDA:
        model.cuda()
        landmark_tensor = landmark_tensor.cuda()

    model.eval()
    cate_predictor = CatePredictor(cfg.data.test, tops_type=[1])

    # Initialize tracker model
    yolo = Create_Yolo(input_size=YOLO_INPUT_SIZE)
    load_yolo_weights(yolo, Darknet_weights)  # use Darknet weights

    while True:
        if q.empty():
            time.sleep(1)
            continue

        recording_id, recording_filename = q.get()

        if recording_id == -1:
            break

        recording_filepath = os.path.join(
            RECORDINGS_DIRECTORY, recording_filename)
        Object_tracking(yolo, webapi, recording_id, recording_filepath, model, cate_predictor, landmark_tensor, iou_threshold=0.1,
                        rectangle_colors=(255, 0, 0), Track_only=["person"])


def main():
    webapi = WebAPI(IP_ADDR, PORT, ACCOUNT, PASSWORD)

    q = queue.Queue()
    p1 = threading.Thread(target=download_recordings, args=([q, webapi]))
    p2 = threading.Thread(target=process_recordings, args=([q, webapi]))
    p1.start()
    p2.start()
    p1.join()
    p2.join()

    webapi.logout()


if __name__ == '__main__':
    main()
