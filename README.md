# HASS-Deepstack
[Home Assistant](https://www.home-assistant.io/) custom components for using Deepstack face &amp; object detection. [Deepstack](https://www.deepquestai.com/insider/) is a service which runs in a docker container and exposes deep-learning models via a REST API. There is no cost for using Deepstack, although you will need a machine with 8 GB RAM. On your machine with docker, pull the latest image (approx. 2GB):

```
sudo docker pull deepquestai/deepstack
```
**Recommended OS** Deepstack docker containers are optimised for Linux or Windows 10 Pro. Mac and regular windows users my experience performance issues.

**GPU users** Note that if your machine has an Nvidia GPU you can get a 5 x 20 times performance boost by using the GPU, [read the docs here](https://deepstackpython.readthedocs.io/en/latest/gpuinstall.html#gpuinstall).

**Legacy machine users** If you are using a machine that doesn't support avx or you are having issues with making requests, Deepstack has a specific build for these systems. Use `deepquestai/deepstack:noavx` instead of `deepquestai/deepstack` when you are installing or running Deepstack.

## Activating the API
Before you get started, you will need to activate the Deepstack API. First, go to www.deepstack.cc and sign up for an account. Choose the basic plan which will give us unlimited access for one installation. You will then see an activation key in your portal.

On your machine with docker, run Deepstack without any recognition so you can activate the API on port `5000`:
```
sudo docker run -v localstorage:/datastore -p 5000:5000 deepquestai/deepstack
```

Now go to http://YOUR_SERVER_IP_ADDRESS:5000/ on another computer or the same one running Deepstack. Input your activation key from your portal into the text box below "Enter New Activation Key" and press enter. Now stop your docker container. You are now ready to start using Deepstack!

## Home Assistant setup
Place the `custom_components` folder in your configuration directory (or add its contents to an existing `custom_components` folder). Then configure face recognition and/or object detection. Note that at we use `scan_interval` to (optionally) limit computation, [as described here](https://www.home-assistant.io/components/image_processing/#scan_interval-and-optimising-resources).

## Face recognition
Deepstack [face recognition](https://deepstackpython.readthedocs.io/en/latest/facerecognition.html) counts faces and will recognise them if you have trained your Deepstack using the `deepstack_teach_face` service.

On you machine with docker, run Deepstack with the face recognition service active on port `5000`:
```
sudo docker run -e VISION-FACE=True -v localstorage:/datastore -p 5000:5000 deepquestai/deepstack
```

The `deepstack_face` component adds an `image_processing` entity where the state of the entity is the total number of faces that are found in the camera image. Recognised faces are listed in the entity `matched faces
` attribute.

Add to your Home-Assistant config:
```yaml
image_processing:
  - platform: deepstack_face
    ip_address: localhost
    port: 5000
    scan_interval: 20000
    source:
      - entity_id: camera.local_file
        name: face_counter
```
Configuration variables:
- **ip_address**: the ip address of your deepstack instance.
- **port**: the port of your deepstack instance.
- **source**: Must be a camera.
- **name**: (Optional) A custom name for the the entity.

#### Service `deepstack_teach_face`
This service is for teaching (or [registering](https://deepstackpython.readthedocs.io/en/latest/facerecognition.html#face-registeration)) faces with deepstack, so that they can be recognised.

Example valid service data:
```
{
  "name": "superman",
  "file_path": "/Users/robincole/.homeassistant/images/superman_1.jpeg"
}
```

<p align="center">
<img src="https://github.com/robmarkcole/HASS-Deepstack/blob/master/docs/face_usage.png" width="500">
</p>

<p align="center">
<img src="https://github.com/robmarkcole/HASS-Deepstack/blob/master/docs/face_detail.png" width="350">
</p>

## Object Detection
Deepstack [object detection](https://deepstackpython.readthedocs.io/en/latest/objectdetection.html) can identify 80 different kinds of objects, including people (`person`) and animals. On you machine with docker, run Deepstack with the object detection service active on port `5000`:
```
sudo docker run -e VISION-DETECTION=True -v localstorage:/datastore -p 5000:5000 deepquestai/deepstack
```

The `deepstack_object` component adds an `image_processing` entity where the state of the entity is the total number of `target` objects that are found in the camera image. The class and number objects of each class is listed in the entity attributes. An event `image_processing.object_detected` is fired for each object detected. Optionally the processed image can be saved to disk. If `save_file_folder` is configured two images are created, one with the filename of format `deepstack_latest_{target}.jpg` which is over-written on each new detection of the `target`, and another with a unique filename including the timestamp.

Add to your Home-Assistant config:
```yaml
image_processing:
  - platform: deepstack_object
    ip_address: localhost
    port: 5000
    scan_interval: 20000
    save_file_folder: /config/www/deepstack_person_images
    target: person
    source:
      - entity_id: camera.local_file
        name: person_detector
```
Configuration variables:
- **ip_address**: the ip address of your deepstack instance.
- **port**: the port of your deepstack instance.
- **save_file_folder**: (Optional) The folder to save processed images to. Note that folder path should be added to [whitelist_external_dirs](https://www.home-assistant.io/docs/configuration/basic/)
- **source**: Must be a camera.
- **target**: The target object class, default `person`.
- **name**: (Optional) A custom name for the the entity.

<p align="center">
<img src="https://github.com/robmarkcole/HASS-Deepstack/blob/master/docs/object_usage.png" width="800">
</p>

<p align="center">
<img src="https://github.com/robmarkcole/HASS-Deepstack/blob/master/docs/object_detail.png" width="350">
</p>

#### Event `image_processing.object_detected`
An event `image_processing.object_detected` is fired for each object detected. An example use case for this is incrementing a [counter](https://www.home-assistant.io/components/counter/) when a person is detected. The `image_processing.object_detected` event payload includes:

- `classifier` : the classifier (i.e. `deepstack_object`)
- `entity_id` : the entity id responsible for the event
- `object` : the object detected
- `confidence` : the confidence in detection in the range 0 - 1 where 1 is 100% confidence.

An example automation using the `image_processing.object_detected` event is given below:

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
    event_type: image_processing.object_detected
    event_data:
      object: person
```

#### Event `image_processing.file_saved`
If `save_file_folder` is configured, an new image will be saved with bounding boxes of detected `target` objects, and the filename will include the time of the image capture. On saving this image a `image_processing.file_saved` event is fired, with a payload that includes:

- `classifier` : the classifier (i.e. `deepstack_object`)
- `entity_id` : the entity id responsible for the event
- `file` : the full path to the saved file

An example automation using the `image_processing.file_saved` event is given below, which sends a Telegram message with the saved file:

```yaml
- action:
  - data_template:
      caption: "Captured {{ trigger.event.data.file }}"
      file: "{{ trigger.event.data.file }}"
    service: telegram_bot.send_photo
  alias: New person alert
  condition: []
  id: '1120092824611'
  trigger:
  - platform: event
    event_type: image_processing.file_saved
```

<p align="center">
<img src="https://github.com/robmarkcole/HASS-Deepstack/blob/master/docs/notification.jpg" width="350">
</p>

The second image created on new detections has a fixed filename to make it easy to display with the [local_file](https://www.home-assistant.io/components/local_file/) camera. An example configuration is:
```yaml
camera:
  - platform: local_file
    file_path: /Users/robincole/.homeassistant/images/deepstack/deepstack_latest_person.jpg
    name: deepstack_latest_person
```

### Face & Object detection
Overall detection can be improved by running both face and object detection, but beware this results in significant memory usage. Configure the two components as above and run Deepstack with:

```
sudo docker run -e VISION-DETECTION=True -e VISION-FACE=True -v localstorage:/datastore -p 5000:5000 deepquestai/deepstack
```

<p align="center">
<img src="https://github.com/robmarkcole/HASS-Deepstack/blob/master/docs/face_and_object_usage.png" width="500">
</p>

### Support
For code related issues such as suspected bugs, please open an issue on this repo. For general chat or to discuss Home Assistant specific issues related to configuration or use cases, please [use this thread on the Home Assistant forums](https://community.home-assistant.io/t/face-and-person-detection-with-deepstack-local-and-free/92041).

### Docker tips
Add the `-d` flag to run the container in background, thanks [@arsaboo](https://github.com/arsaboo).

### FAQ
Q1: I get the following warning, is this normal?
```
2019-01-15 06:37:52 WARNING (MainThread) [homeassistant.loader] You are using a custom component for image_processing.deepstack_face which has not been tested by Home Assistant. This component might cause stability problems, be sure to disable it if you do experience issues with Home Assistant.
```
A1: Yes this is normal

------

Q2: Why are there two custom components and not just one?

A2: It is easier to maintain two simple components than one complex one.

------

Q3: The API return bounding boxes, why does this component not expose them?

A3: The Home Assistant developers team are currently figuring out how bounding boxes should be handed, please feel free to add your thoughts to [this issue](https://github.com/home-assistant/architecture/issues/133).

------

Q4: Will Deepstack always be free, if so how do these guys make a living?

A4: I'm informed there will always be a basic free version with preloaded models, while there will be an enterprise version with advanced features such as custom models and endpoints, which will be subscription based.

------

Q5: What are the minimum hardware requirements for running Deepstack?

A5. Based on my experience, I would allow 0.5 GB RAM per model.

------

Q6: Whats security like on the Deepstack container? Auth, SSL?

A6: None yet, the Deepstack team are working on it.

------

Q7: Can object detection be configured to detect car/car colour?

A7: The list of detected object classes is at the end of the page [here](https://deepstackpython.readthedocs.io/en/latest/objectdetection.html). There is no support for detecting the colour of an object.

------

Q8: If I teach (register) a face do I need to re-teach if I restart the container?

A8: So long as you have run the container including `-v localstorage:/datastore` then you do not need to re-teach, as data is persisted between restarts.

------
