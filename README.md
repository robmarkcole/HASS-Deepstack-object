# HASS-Deepstack
[Home Assistant](https://www.home-assistant.io/) custom components for using Deepstack face recognition &amp; object detection. [Deepstack](https://www.deepquestai.com/insider/) is a service which runs in a docker container and exposes deep-learning models via a REST API. There is no cost for using Deepstack, although you will need a machine with 8 GB RAM. On your machine with docker, pull the latest image (approx. 2GB):

```
sudo docker pull deepquestai/deepstack
```

**GPU users** Note that if your machine has an Nvidia GPU you can get a 5 x 20 times performance boost by using the GPU, [read the docs here](https://deepstackpython.readthedocs.io/en/latest/gpuinstall.html#gpuinstall).

## Home Assistant setup
Place the `custom_components` folder in your configuration directory (or add its contents to an existing `custom_components` folder). Then configure face recognition and/or object detection.

## Face Recognition
On you machine with docker, run Deepstack with the face recognition service active on port `5000`:
```
sudo docker run -e VISION-FACE=True -v localstorage:/datastore -p 5000:5000 deepquestai/deepstack
```

The `deepstack_face` component adds an `image_processing` entity where the state of the entity is the total number of faces that are found in the camera image. The gender of faces is listed in the entity attributes.

Add to your Home-Assistant config:
```yaml
image_processing:
  - platform: deepstack_face
    ip_address: localhost
    port: 5000
    source:
      - entity_id: camera.local_file
        name: face_counter
```
Configuration variables:
- **ip_address**: the ip address of your deepstack instance.
- **port**: the port of your deepstack instance.
- **source**: Must be a camera.
- **name**: (Optional) A custom name for the the entity.

<p align="center">
<img src="https://github.com/robmarkcole/HASS-Deepstack/blob/master/docs/usage.png" width="500">
</p>

<p align="center">
<img src="https://github.com/robmarkcole/HASS-Deepstack/blob/master/docs/detail.png" width="350">
</p>

## Object Detection
On you machine with docker, run Deepstack with the object detection service active on port `5000`:
```
sudo docker run -e VISION-DETECTION=True -v localstorage:/datastore -p 5000:5000 deepquestai/deepstack
```

The `deepstack_object` component adds an `image_processing` entity where the state of the entity is the total number of `target` objects that are found in the camera image. The class and number objects of each class is listed in the entity attributes.

Add to your Home-Assistant config:
```yaml
image_processing:
  - platform: deepstack_object
    ip_address: localhost
    port: 5000
    target: person
    source:
      - entity_id: camera.local_file
        name: person_detector
```
Configuration variables:
- **ip_address**: the ip address of your deepstack instance.
- **port**: the port of your deepstack instance.
- **source**: Must be a camera.
- **target**: The target object class, default `person`.
- **name**: (Optional) A custom name for the the entity.

<p align="center">
<img src="https://github.com/robmarkcole/HASS-Deepstack/blob/master/docs/object_usage.png" width="800">
</p>

<p align="center">
<img src="https://github.com/robmarkcole/HASS-Deepstack/blob/master/docs/object_detail.png" width="350">
</p>

### Face & Object detection
Overall detection can be improved by running both face and object detection, but beware this results in significant memory usage. Configure the two components as above and run Deepstack with:

```
sudo docker run -e VISION-DETECTION=True -e VISION-FACE=True -v localstorage:/datastore -p 5000:5000 deepquestai/deepstack
```

<p align="center">
<img src="https://github.com/robmarkcole/HASS-Deepstack/blob/master/docs/face_and_object_usage.png" width="500">
</p>

### FAQ
Q1: I get the following warning, is this normal?
```
2019-01-15 06:37:52 WARNING (MainThread) [homeassistant.loader] You are using a custom component for image_processing.deepstack_face which has not been tested by Home Assistant. This component might cause stability problems, be sure to disable it if you do experience issues with Home Assistant.
```
A1: Yes this is normal

Q2: Why are there two custom components and not just one?
A2: Its easier to maintain tow simple components than one complex one.
