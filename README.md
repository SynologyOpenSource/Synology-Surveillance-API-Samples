# Synology Surveillance API Samples
This repository demonstrate how to use python to call Web APIs in Synology Surveillance Station and integrate with your own request!

## Why Synology-Surveillance-API-Samples?
Using the Synology-Surveillance-API-Samples is convenient for you to integrate with Synology Surveillance. You can refer to the example to see how does it work.

When to use Synology-Surveillance-API-Samples
* If you want to integrate your system with Synology Surveillance
* If you want to integrate your analytics with live stream or recordings in Synology Surveillance

## Features
* [Live - stream analyze](./live-stream/README.md)
  * We'll demonstrate how to get the camera's live stream and analyze it with your own model. We develop a fall detection model as an example.
* [Recording analyze and add bookmark](./recording-bookmark/README.md)
  * We’ll demonstrate how to analyze existing recordings with your own model and
add book mark to important timing. We develop a clothe model as an example.

## Prepare your environment
### Dependencies (Web API parts)
* requests
* opencv-python

```
pip install -r requirements.txt
```

### External deep learning projects
* [TensorFlow-2.x-YOLOv3](https://github.com/pythonlessons/TensorFlow-2.x-YOLOv3)
* [mmfashion](https://github.com/open-mmlab/mmfashion)

NOTE: You need follow the installation guide of these projects to install properly.
