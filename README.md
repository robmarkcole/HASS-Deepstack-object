# HASS-Deepstack-object
[Home Assistant](https://www.home-assistant.io/) custom component for Deepstack object detection. [Deepstack](https://python.deepstack.cc/) is a service which runs in a docker container and exposes deep-learning models via a REST API. Deepstack [object detection](https://python.deepstack.cc/object-detection) uses [Yolo V3](https://pjreddie.com/darknet/yolo/) to identify 80 different kinds of objects, including people (`person`) and animals. There is no cost for using Deepstack, although you will need a machine with 8 GB RAM. On your machine with docker, pull the latest image (approx. 2GB):

```
docker pull deepquestai/deepstack
```
OR, if you are using a legacy machine:
```
docker pull deepquestai/deepstack:noavx
```
**Recommended OS** Deepstack docker containers are optimised for Linux or Windows 10 Pro. Mac and regular windows users my experience performance issues. [You can also run deepstack on a Raspberry pi](https://python.deepstack.cc/raspberry-pi) if you own an Intel NCS (Movidius) stick (approx $70).

**GPU users** Note that if your machine has an Nvidia GPU you can get a 5 x 20 times performance boost by using the GPU.

**Legacy machine users** If you are using a machine that doesn't support avx or you are having issues with making requests, Deepstack has a specific build for these systems. Use `deepquestai/deepstack:noavx` instead of `deepquestai/deepstack` when you are installing or running Deepstack. I expect many users will be using noavx mode so I will use it in the examples below.

## Activating the Deepstack API
Before you get started, you will need to activate the Deepstack API. First, go to www.deepstack.cc and sign up for an account. Choose the basic plan which will give us unlimited access for one installation. You will then see an activation key in your portal.

On your machine with docker, run Deepstack (noavx mode) without any recognition so you can activate the API on port `5000`:
```
docker run -v localstorage:/datastore -p 5000:5000 deepquestai/deepstack:noavx
```

Now go to http://YOUR_SERVER_IP_ADDRESS:5000/ on another computer or the same one running Deepstack. Input your activation key from your portal into the text box below "Enter New Activation Key" and press enter. Now stop your docker container, and restart and run Deepstack (noavx mode) with the object detection service active on port `5000`:
```
docker run -e VISION-DETECTION=True -e API-KEY="mysecretkey" -v localstorage:/datastore -p 5000:5000 --name deepstack deepquestai/deepstack:noavx
```
You can test the endpoint is active using [curl](https://curl.haxx.se/), from within a directory containing an image `test.jpg`:
```
curl -X POST -F image=@couple.jpg 'http://localhost:5000/v1/vision/detection'
```
Which should return something like:
```json
{"success":true,
"predictions":[
    {"confidence":0.99967474,"label":"person","y_min":25,"x_min":1184,"y_max":2692,"x_max":2277},
    {"confidence":0.997645,"label":"person","y_min":148,"x_min":460,"y_max":2655,"x_max":1348},
    {"confidence":0.9949693,"label":"tie","y_min":757,"x_min":1731,"y_max":1407,"x_max":1857}]}
```

## Usage of this component
The `deepstack_object` component adds an `image_processing` entity where the state of the entity is the total count of target objects that are above a `confidence` threshold which has a default value of 80%. You can have a single target object class, or multiple. The time of the last detection of any target object is in the `last target detection` attribute. The type and number of objects (of any confidence) is listed in the `summary` attributes. Optionally the processed image can be saved to disk, with bounding boxes showing the location of detected objects. If `save_file_folder` is configured, an image with filename of format `deepstack_object_{source name}_latest.jpg` is over-written on each new detection of a target. Optionally this image can also be saved with a timestamp in the filename, if `save_timestamped_file` is configured as `True`. An event `deepstack.object_detected` is fired for each object detected. If you are a power user with advanced needs such as zoning detections or you want to track multiple object types, you will need to use the `deepstack.object_detected` events.

**Note** that by default the component will **not** automatically scan images, but requires you to call the `image_processing.scan` service e.g. using an automation triggered by motion.

## Home Assistant setup
Place the `custom_components` folder in your configuration directory (or add its contents to an existing `custom_components` folder). Then configure object detection. **Important:** It is necessary to configure only a single camera per `deepstack_object` entity. If you want to process multiple cameras, you will therefore need multiple `deepstack_object` `image_processing` entities.

The component can optionally save snapshots of the processed images. If you would like to use this option, you need to create a folder where the snapshots will be stored. The folder should be in the same folder where your `configuration.yaml` file is located. In the example below, we have named the folder `snapshots`.

Add to your Home-Assistant config:

```yaml
image_processing:
  - platform: deepstack_object
    ip_address: localhost
    port: 5000
    api_key: mysecretkey
    save_file_folder: /config/snapshots/
    save_timestamped_file: True
    targets:
      - person
      - car
    source:
      - entity_id: camera.local_file
```

Configuration variables:
- **ip_address**: the ip address of your deepstack instance.
- **port**: the port of your deepstack instance.
- **api_key**: (Optional) Any API key you have set.
- **timeout**: (Optional, default 10 seconds) The timeout for requests to deepstack.
- **save_file_folder**: (Optional) The folder to save processed images to. Note that folder path should be added to [whitelist_external_dirs](https://www.home-assistant.io/docs/configuration/basic/)
- **save_timestamped_file**: (Optional, default `False`, requires `save_file_folder` to be configured) Save the processed image with the time of detection in the filename.
- **source**: Must be a camera.
- **targets**: The list of target objects, default `person`.
- **confidence**: (Optional) The confidence (in %) above which detected targets are counted in the sensor state. Default value: 80
- **name**: (Optional) A custom name for the the entity.

<p align="center">
<img src="https://github.com/robmarkcole/HASS-Deepstack-object/blob/master/docs/object_usage.png" width="500">
</p>

<p align="center">
<img src="https://github.com/robmarkcole/HASS-Deepstack-object/blob/master/docs/object_detail.png" width="350">
</p>

#### Event `deepstack.object_detected`
An event `deepstack.object_detected` is fired for each object detected above the configured `confidence` threshold. This is the recommended way to check the confidence of detections, and to keep track of objects that are not configured as the `target` (use `Developer tools -> EVENTS -> :Listen to events`, to monitor these events). 

An example use case for event is to get an alert when some rarely appearing object is detected, or to increment a [counter](https://www.home-assistant.io/components/counter/). The `deepstack.object_detected` event payload includes:

- `entity_id` : the entity id responsible for the event
- `object` : the object detected
- `confidence` : the confidence in detection in the range 0 - 1 where 1 is 100% confidence.
- `box` : the bounding box of the object
- `centroid` : the centre point of the object

An example automation using the `deepstack.object_detected` event is given below:

```yaml
- action:
  - data_template:
      title: "New object detection"
      message: "{{ trigger.event.data.object }} with confidence {{ trigger.event.data.confidence }}"
    service: notify.pushbullet
  alias: Object detection automation
  condition: []
  id: '1120092824622'
  trigger:
  - platform: event
    event_type: deepstack.object_detected
    event_data:
      object: person
```

The `box` coordinates and the box center (`centroid`) can be used to determine whether an object falls within a defined region-of-interest (ROI). This can be useful to include/exclude objects by their location in the image.

* The `box` is defined by the tuple `(y_min, x_min, y_max, x_max)` (equivalent to image top, left, bottom, right) where the coordinates are floats in the range `[0.0, 1.0]` and relative to the width and height of the image.
* The centroid is in `(x,y)` coordinates where `(0,0)` is the top left hand corner of the image and `(1,1)` is the bottom right corner of the image.


## Displaying the deepstack latest jpg file
It easy to display the `deepstack_object_{source name}_latest.jpg` image with a [local_file](https://www.home-assistant.io/components/local_file/) camera. An example configuration is:
```yaml
camera:
  - platform: local_file
    file_path: /config/snapshots/deepstack_object_local_file_latest.jpg
    name: deepstack_latest_person
```

## Automation using deepstack latest jpg file
I am using an automation to send a photo notification when there is a new detection. This requires you to setup the [folder_watcher](https://www.home-assistant.io/integrations/folder_watcher/) integration first. Then in `automations.yaml` I have:

```yaml
- id: '3287784389530'
  alias: Deepstack person alert
  trigger:
    event_type: folder_watcher
    platform: event
    event_data:
      event_type: modified
      path: '/config/www/deepstack_object_local_file_latest.jpg'
  action:
    service: telegram_bot.send_photo
    data_template:
      caption: Person detected
      file: '/config/www/deepstack_object_local_file_latest.jpg'
```

## Face recognition
For face recognition with Deepstack use https://github.com/robmarkcole/HASS-Deepstack-face

## Google Coral USB stick
If you have a [Google Coral USB stick](https://coral.withgoogle.com/products/accelerator/) you can use it as a drop in replacement for Deepstack object detection by using the [coral-pi-rest-server](https://github.com/robmarkcole/coral-pi-rest-server). Note that the predictions may differ from those provided by Deepstack.

### Support
For code related issues such as suspected bugs, please open an issue on this repo. For general chat or to discuss Home Assistant specific issues related to configuration or use cases, please [use this thread on the Home Assistant forums](https://community.home-assistant.io/t/face-and-person-detection-with-deepstack-local-and-free/92041).

### Docker tips
Add the `-d` flag to run the container in background

### FAQ
Q1: I get the following warning, is this normal?
```
2019-01-15 06:37:52 WARNING (MainThread) [homeassistant.loader] You are using a custom component for image_processing.deepstack_face which has not been tested by Home Assistant. This component might cause stability problems, be sure to disable it if you do experience issues with Home Assistant.
```
A1: Yes this is normal

------

Q2: Will Deepstack always be free, if so how do these guys make a living?

A2: Enterprise support pays the developers salaries.

------

Q3: What are the minimum hardware requirements for running Deepstack?

A3. Based on my experience, I would allow 0.5 GB RAM per model.

------

Q4: Can object detection be configured to detect car/car colour?

A4: The list of detected object classes is at the end of the page [here](https://deepstackpython.readthedocs.io/en/latest/objectdetection.html). There is no support for detecting the colour of an object.

------

Q5: I am getting an error from Home Assistant: `Platform error: image_processing - Integration deepstack_object not found`

A5: This can happen when you are running in Docker/Hassio, and indicates that one of the dependencies isn't installed. It is necessary to reboot your Hassio device, or rebuild your Docker container. Note that just restarting Home Assistant will not resolve this.

------

## Development
Currently only the helper functions are tested, using pytest.
* `python3 -m venv venv`
* `source venv/bin/activate`
* `pip install -r requirements-dev.txt`
* `venv/bin/py.test custom_components/deepstack_object/tests.py -vv -p no:warnings`