import requests
import json
import queue
import threading
import time
import cv2
import math
import os
from utils import get_latest_frame

# replace the following with your NVR and user account
IP_ADDR = 'xxx.xxx.xxx.xxx'
PORT = 'xxxx'
ACCOUNT = 'xxxxxx'
PASSWORD = 'xxxxxx'


# replace the following tokens with the ones from your Action Rule settings
SEND_NOTIFICATION_TOKEN = '1GRSPdGqYnOPjoNtiY0XiLEyX8GiL2FsVBdPOwvm3cmzjZ5ujxZpmNVkshP4iWpJ'
ACTION_RULE_RECORDING_TOKEN = 'kG5wxbuXjCn27QmykHywMx6NxkwjJaFf7g5SwPe8r6gl70xVGJun9ow4rXHTxwEe'


class WebAPI:
    """This is a wrapper class which has Synology Surveillance Station Web API methods.
    """
    GET_REQUEST = 0
    POST_REQUEST = 1

    def __init__(self, ip_addr, port, account, password):
        """ WebAPI constructor

        :param ip_addr: (str)
        :param port: (str)
        :param account: (str)
        :param password: (str)
        """
        self.ip_port = '{}:{}'.format(ip_addr, port)
        self.sid = self.login(account, password)

    def send_request(self, api, payload, request_type):
        """ Send request to call Web API

        :param api: (str) the API to be called
        :param payload: (dict) the parameters for the desired API method
        :param request_type: (int) GET_REQUEST or POST_REQUEST
        :return: (dict) response from Web API request
        """
        url = '{}{}'.format(self.ip_port, api)

        if request_type == self.GET_REQUEST:
            r = requests.get(url, params=payload).json()
        elif request_type == self.POST_REQUEST:
            r = requests.post(url, data=payload).json()
        else:
            raise NameError('Invalid request type!')

        if not r['success']:
            web_API_document = 'https://global.download.synology.com/download/Document/Software/DeveloperGuide/Package/SurveillanceStation/All/enu/Surveillance_Station_Web_API.pdf'
            error_message = '{} {}\n{}\n'.format(
                api, 'request failed.\nPlease go to the following website to read the error code for this API.', web_API_document)
            raise NameError(error_message)

        return r

    def login(self, account, password):
        """ Login to Surveillance Station

        :param account: (str)
        :param password: (str)
        :return: (str) session id of this login
        """
        api = '/webapi/auth.cgi?api=SYNO.API.Auth'

        payload = {'method': 'Login',
                   'version': 6,
                   'account': account,
                   'passwd': password,
                   'session': 'SurveillanceStation',
                   'format': 'sid'}

        r = self.send_request(api, payload, self.GET_REQUEST)
        sid = r['data']['sid']

        return sid

    def logout(self):
        """ Logout Surveillance Station

        :return: (dict) response from Web API request
        """
        api = '/webapi/auth.cgi?api=SYNO.API.Auth'

        payload = {'method': 'Logout',
                   'version': 6,
                   '_sid': self.sid}

        r = self.send_request(api, payload, self.GET_REQUEST)
        return r

    def list_cameras(self):
        """ List all the cameras in the Surveillance Station

        :return: (list) list of cameras in the Surveillance Station
        """
        api = '/webapi/entry.cgi?api=SYNO.SurveillanceStation.Camera'

        payload = {'method': 'List',
                   'version': 9,
                   'privCamType': 1,
                   'camStm': 0,
                   '_sid': self.sid}

        r = self.send_request(api, payload, self.GET_REQUEST)
        cameras = r['data']['cameras']

        return cameras

    def list_recordings(self, camera_ids=[]):
        """ List all the recordings in the Surveillance Station. If camera_ids is not given, 
        this method will get recordings from all the cameras in the Surveillance Station.

        :param camera_ids: (list) list of camera_id(int)
        :return: (list) list of recordings
        """

        api = '/webapi/entry.cgi?api=SYNO.SurveillanceStation.Recording'

        payload = {'method': 'List',
                   'version': 5,
                   '_sid': self.sid}

        if len(camera_ids) > 0:
            payload['cameraIds'] = ','.join(
                [str(camera_id) for camera_id in camera_ids])

        r = self.send_request(api, payload, self.GET_REQUEST)
        recordings = r['data']['events']

        return recordings

    def get_liveview_rtsp(self, camera_id):
        """ Get the rtsp path of a specific camera

        :param camera_id: (int)
        :return: (str) rtsp path of the camera
        """
        api = '/webapi/entry.cgi?api=SYNO.SurveillanceStation.Camera'

        payload = {'method': 'GetLiveViewPath',
                   'version': 9,
                   'idList': str(camera_id),
                   '_sid': self.sid}

        r = self.send_request(api, payload, self.GET_REQUEST)
        rtsp = r['data'][0]['rtspPath']

        return rtsp

    def send_notification(self):
        """ Send notification to users.
        Please follow the setup in live-stream/README.md before you use this method.

        :return: (dict) response from Web API request
        """
        api = '/webapi/entry.cgi?api=SYNO.SurveillanceStation.Webhook'

        payload = {'method': 'Incoming',
                   'version': 1,
                   'token': SEND_NOTIFICATION_TOKEN}

        r = self.send_request(api, payload, self.GET_REQUEST)
        return r

    def start_action_rule_recording(self):
        """ Start action Rule Recording from a specific camera.
        Please follow the setup in live-stream/README.md before you use this method.

        :return: (dict) response from Web API request
        """
        api = '/webapi/entry.cgi?api=SYNO.SurveillanceStation.Webhook'

        payload = {'method': 'Incoming',
                   'version': 1,
                   'token': ACTION_RULE_RECORDING_TOKEN}

        r = self.send_request(api, payload, self.GET_REQUEST)
        return r

    def _get_available_type_index(self, setting):
        """ helper function of create_recording_label

        :return: (int) an available type index for a new label category in Recording app
        """
        if len(setting) == 0:
            return 1

        max_label_id = 0

        for label in setting:
            max_label_id = max(label['type'], max_label_id)

        full_length = int(math.log(max_label_id, 2)) + 1

        if len(setting) == full_length:
            return max_label_id << 1
        else:
            occupy = [False] * full_length

            for label in setting:
                index = int(math.log(label['type'], 2))
                occupy[index] = True

            for i, occupied in enumerate(occupy):
                if not occupied:
                    return 1 << i

    def _get_label_setting(self):
        """ helper function of create_recording_label

        :return: (list) all the label settings in Recording app
        """
        api = '/webapi/entry.cgi?api=SYNO.SurveillanceStation.Recording'

        payload = {'method': 'GetLabelSetting',
                   'version': 5,
                   '_sid': self.sid}

        r = self.send_request(api, payload, self.GET_REQUEST)
        return r['data']['setting']

    def _set_label_setting(self, setting):
        """ helper function for create_recording_label and erase_recording_labels.

        :param setting: (list) desired label setting to set label categories in Recording app
        :return: (dict) response from Web API request
        """
        api = '/webapi/entry.cgi?api=SYNO.SurveillanceStation.Recording'

        payload = {'method': 'SetLabelSetting',
                   'version': 5,
                   'setting': json.dumps(setting),
                   '_sid': self.sid}

        r = self.send_request(api, payload, self.POST_REQUEST)
        return r

    def _save_tag(self, recording_id, custom_label):
        """ helper function for add_label_to_recording, remove_label_on_recording and clean_labels_on_recording

        :param recording_id: (int) the id of the recording to be set
        :param custom_label: (int) the 'bit-wise or' value of all the desired label type indexes for this recording
        :return: (dict) response from Web API request
        """
        api = '/webapi/entry.cgi?api=SYNO.SurveillanceStation.Recording'

        payload = {'method': 'SaveTag',
                   'version': 5,
                   'archId': 0,
                   'customLabel': custom_label,
                   'id': recording_id,
                   'systemLabel': 0,
                   '_sid': self.sid}

        r = self.send_request(api, payload, self.POST_REQUEST)
        return r

    def _get_tag(self, recording_id):
        """ helper function for add_label_to_recording and remove_label_on_recording

        :param recording_id: (int) the id of the recording
        :return: (int) the 'bit-wise or' value of all the label type indexes on this recording
        """
        recordings = self.list_recordings()

        for recording in recordings:
            if recording['id'] == recording_id:
                return recording['customLabel']

        raise NameError('recording_id {} does not exist!'.format(recording_id))

    def create_recording_label(self, name):
        """Create a new label category on Recording app
        The type(label_id) for a label setting is by bit position. 
        For example, when you create the first label, it's type is 1, 
        the second is 2, the third is 4, and so on.
        To add a new category, we have to use SetLabelSetting method in
        SYNO.SurveillanceStation.Recording Web API. 
        However, when we use this method, we have to give it all the label settings,
        including the new one and all the other previous ones. 
        As a result, we have to get previous label settings, add a new label setting,
        then call SetLabelSetting method.

        :param name: (str) name of the label category
        :return: (int) label id of the created category
        """

        setting = self._get_label_setting()
        label_id = self._get_available_type_index(setting)

        setting.append({'categ': 2,
                        'enabled': True,
                        'text': name,
                        'background': '#E3D000',
                        'createTime': int(time.time()),
                        'type': label_id})

        r = self._set_label_setting(setting)
        return label_id

    def delete_recording_label(self, label_id):
        """ Delete a label category on Recording app

        :param label_id: (int) the id of the label to be deleted
        :return: (dict) response from Web API request
        """
        api = '/webapi/entry.cgi?api=SYNO.SurveillanceStation.Recording'

        payload = {'method': 'DeleteLabel',
                   'version': 5,
                   'customLabel': label_id,
                   '_sid': self.sid}

        r = self.send_request(api, payload, self.POST_REQUEST)
        return r

    def erase_recording_labels(self):
        """ Erase all label categories on Recording app

        :return: (dict) response from Web API request
        """
        r = self._set_label_setting([])
        return r

    def add_label_to_recording(self, recording_id, label_id):
        """ Add a label to a specific recording in Recording app
        The type(label_id) for a label setting is by bit position.
        For example, when you create the first label, it's type is 1,
        the second is 2, the third is 4, and so on.
        Therefore, when we want to add labels to a recording, we simply 
        'bitwise or' all the type(label_id) for each label. 
        Then, use that as customLabel parameter for SaveTag method 
        in SYNO.SurveillanceStation.Recording Web API.

        :param recording_id: (int) the id of the recording to add label
        :param label_id: (int) the id of the label
        :return: (dict) response from Web API request
        """
        custom_label = self._get_tag(recording_id) | label_id
        r = self._save_tag(recording_id, custom_label)

        return r

    def remove_label_on_recording(self, recording_id, label_id):
        """ Remove a label on a specific recording in Recording app

        :param recording_id: (int) the id of the recording to remove label
        :param label_id: (int) the id of the label to be removed from the recording
        :return: (dict) response from Web API request
        """
        custom_label = self._get_tag(recording_id)
        if custom_label & label_id:
            custom_label ^= label_id
            r = self._save_tag(recording_id, custom_label)
        else:
            raise NameError('label_id {} does not exist on recording {}!'.format(
                label_id, recording_id))

        return r

    def clean_labels_on_recording(self, recording_id):
        """ Clean all labels on a specific recording in Recording app

        :param recording_id: (int) the id of the recording
        :return: (dict) response from Web API request
        """
        r = self._save_tag(recording_id, 0)
        return r

    def download_recording(self, recording_id, recording_storing_path):
        """ Download a specific recording
        We can also use Download method in SYNO.SurveillanceStation.Recording.
        However, if we use that, we cannot get the timestamp of the recording
        since its filename is something like: example_recording-20200827-141256.mp4
        On the contrast, when we download recording with this method, 
        we can get the timestamp in the end of the filename, such as
        example_recording-20200827-141256-1598508776.mp4

        :param recording_id: (int) the id of the recording to be downloaded
        :param recording_storing_path: (str) path to put the downloaded recording
        :return: (str) filename of the downloaded recording
        """
        api = '/webapi/entry.cgi?api=SYNO.SurveillanceStation.Recording.ShareRecording'

        payload = {'method': 'EnableShare',
                   'version': 1,
                   'id': recording_id,
                   'blHttps': 'false',
                   'evtSrcId': 0,
                   'evtType': 0,
                   '_sid': self.sid}

        r = self.send_request(api, payload, self.POST_REQUEST)
        link = r['data']['evtDownloadLink']

        content = requests.get(self.ip_port + link).content
        filename = link.replace('?', '/').split('/')[3]

        open(os.path.join(recording_storing_path, filename), 'wb').write(content) 
        return filename

    def add_bookmark(self, recording_id, name, comment, timestamp):
        """ Add bookmark to a specific recording

        :param recording_id: (int) the id of the recording to add bookmark
        :param name: (str) name of the bookmark
        :param comment: (str) comment of the bookmark
        :param timestamp: (int) timestamp for the starting time of the recording
        :return: (dict) response from Web API request
        """
        api = '/webapi/entry.cgi?api=SYNO.SurveillanceStation.Recording.Bookmark'

        payload = {'method': 'SaveBookmark',
                   'version': 1,
                   'eventId': recording_id,
                   'name': name,
                   'comment': comment,
                   'timestamp': timestamp,
                   '_sid': self.sid}

        r = self.send_request(api, payload, self.POST_REQUEST)
        return r


def read_frame(q, rtsp):
    stream = cv2.VideoCapture(rtsp)

    while True:
        ret, frame = stream.read()

        if ret:
            q.put(frame)


def process_frame(q):
    while True:
        frame = get_latest_frame(q)
        cv2.imwrite('rtsp-frame.jpg', frame)


def test():
    webapi = WebAPI(IP_ADDR, PORT, ACCOUNT, PASSWORD)

    cameras = webapi.list_cameras()
    camera_ids = [camera['id'] for camera in cameras]

    if len(camera_ids) > 0:
        # the last added camera in the Surveillance Station
        camera_id = camera_ids[-1]
    else:
        raise LookupError('There is no camera in the Serveillance Station!')

    recordings = webapi.list_recordings([camera_id])
    recording_ids = [recording['id'] for recording in recordings]

    recording_id = recording_ids[1]
    filename = webapi.download_recording(recording_id, './')

    timestamp = int(os.path.splitext(filename)[0].split('-')[-1])
    webapi.add_bookmark(recording_id, "Title", "Comment", timestamp)

    rtsp = webapi.get_liveview_rtsp(camera_id)

    label_1 = webapi.create_recording_label('aaa')
    label_2 = webapi.create_recording_label('bbb')
    label_3 = webapi.create_recording_label('ccc')
    webapi.delete_recording_label(label_2)
    webapi.delete_recording_label(label_1)
    label_1 = webapi.create_recording_label('ddd')
    webapi.add_label_to_recording(recording_ids[-1], label_1)
    webapi.add_label_to_recording(recording_ids[-1], label_3)
    webapi.remove_label_on_recording(recording_ids[-1], label_1)

    q = queue.Queue()
    p1 = threading.Thread(target=read_frame, args=([q, rtsp]))
    p2 = threading.Thread(target=process_frame, args=([q]))
    p1.start()
    p2.start()
 
    p1.join()
    p2.join()

    webapi.logout()


if __name__ == '__main__':
    test()
