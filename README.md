# HASS-Deepstack-object
[Home Assistant](https://www.home-assistant.io/) custom component for Deepstack object detection. [Deepstack](https://docs.deepstack.cc/) is a service which runs in a docker container and exposes various computer vision models via a REST API. Deepstack [object detection](https://docs.deepstack.cc/object-detection/index.html) can identify 80 different kinds of objects (listed at bottom of this readme), including people (`person`), vehicles and animals. Alternatively a custom object detection model can be used. There is no cost for using Deepstack and it is [fully open source](https://github.com/johnolafenwa/DeepStack). To run Deepstack you will need a machine with 8 GB RAM, or an NVIDIA Jetson.

On your machine with docker, run Deepstack with the object detection service active on port `80`:
```
docker run -e VISION-DETECTION=True -e API-KEY="mysecretkey" -v localstorage:/datastore -p 80:5000 deepquestai/deepstack
```

## Usage of this component
The `deepstack_object` component adds an `image_processing` entity where the state of the entity is the total count of target objects that are above a `confidence` threshold which has a default value of 80%. You can have a single target object class, or multiple. The time of the last detection of any target object is in the `last target detection` attribute. The type and number of objects (of any confidence) is listed in the `summary` attributes. Optionally a region of interest (ROI) can be configured, and only objects with their center (represented by a `x`) within the ROI will be included in the state count. The ROI will be displayed as a green box, and objects with their center in the ROI have a red box.

Also optionally the processed image can be saved to disk, with bounding boxes showing the location of detected objects. If `save_file_folder` is configured, an image with filename of format `deepstack_object_{source name}_latest.jpg` is over-written on each new detection of a target. Optionally this image can also be saved with a timestamp in the filename, if `save_timestamped_file` is configured as `True`. An event `deepstack.object_detected` is fired for each object detected that is in the targets list, and meets the confidence and ROI criteria. If you are a power user with advanced needs such as zoning detections or you want to track multiple object types, you will need to use the `deepstack.object_detected` events.

**Note** that by default the component will **not** automatically scan images, but requires you to call the `image_processing.scan` service e.g. using an automation triggered by motion.

## Home Assistant setup
Place the `custom_components` folder in your configuration directory (or add its contents to an existing `custom_components` folder). Then configure object detection. **Important:** It is necessary to configure only a single camera per `deepstack_object` entity. If you want to process multiple cameras, you will therefore need multiple `deepstack_object` `image_processing` entities.

The component can optionally save snapshots of the processed images. If you would like to use this option, you need to create a folder where the snapshots will be stored. The folder should be in the same folder where your `configuration.yaml` file is located. In the example below, we have named the folder `snapshots`.

Add to your Home-Assistant config:

```yaml
image_processing:
  - platform: deepstack_object
    ip_address: localhost
    port: 80
    api_key: mysecretkey
    # custom_model: mask
    # confidence: 80
    save_file_folder: /config/snapshots/
    save_timestamped_file: True
    always_save_latest_jpg: True
    scale: 0.75
    # roi_x_min: 0.35
    roi_x_max: 0.8
    #roi_y_min: 0.4
    roi_y_max: 0.8
    targets:
      - target: person
      - target: vehicle
        confidence: 60
      - target: car
        confidence: 40
    source:
      - entity_id: camera.local_file
```

Configuration variables:
- **ip_address**: the ip address of your deepstack instance.
- **port**: the port of your deepstack instance.
- **api_key**: (Optional) Any API key you have set.
- **timeout**: (Optional, default 10 seconds) The timeout for requests to deepstack.
- **custom_model**: (Optional) The name of a custom model if you are using one. Don't forget to add the targets from the custom model below
- **confidence**: (Optional) The confidence (in %) above which detected targets are counted in the sensor state. Default value: 80
- **save_file_folder**: (Optional) The folder to save processed images to. Note that folder path should be added to [whitelist_external_dirs](https://www.home-assistant.io/docs/configuration/basic/)
- **save_timestamped_file**: (Optional, default `False`, requires `save_file_folder` to be configured) Save the processed image with the time of detection in the filename.
- **always_save_latest_jpg**: (Optional, default `False`, requires `save_file_folder` to be configured) Always save the last processed image, even if there were no detections.
- **scale**: (optional, default 1.0), range 0.1-1.0, applies a scaling factor to the images that are saved. This reduces the disk space used by saved images, and is especially beneficial when using high resolution cameras.
- **show_boxes**: (optional, default `True`), if `False` bounding boxes are not shown on saved images
- **roi_x_min**: (optional, default 0), range 0-1, must be less than roi_x_max
- **roi_x_max**: (optional, default 1), range 0-1, must be more than roi_x_min
- **roi_y_min**: (optional, default 0), range 0-1, must be less than roi_y_max
- **roi_y_max**: (optional, default 1), range 0-1, must be more than roi_y_min
- **source**: Must be a camera.
- **targets**: The list of target object names and/or `object_type`, default `person`. Optionally a `confidence` can be set for this target, if not the default confidence is used. Note the minimum possible confidence is 10%.

For the ROI, the (x=0,y=0) position is the top left pixel of the image, and the (x=1,y=1) position is the bottom right pixel of the image. It might seem a bit odd to have y running from top to bottom of the image, but that is the coordinate system used by pillow.

I created an app for exploring the config parameters at [https://github.com/robmarkcole/deepstack-ui](https://github.com/robmarkcole/deepstack-ui)

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
- `name` : the name of the object detected
- `object_type` : the type of the object, from `person`, `vehicle`, `animal` or `other`
- `confidence` : the confidence in detection in the range 0 - 100%
- `box` : the bounding box of the object
- `centroid` : the centre point of the object
- `saved_file` : the path to the saved annotated image, which is the timestamped file if `save_timestamped_file` is True, or the default saved image if False

An example automation using the `deepstack.object_detected` event is given below:

```yaml
- action:
    - data_template:
        caption: "New person detection with confidence {{ trigger.event.data.confidence }}"
        file: "{{ trigger.event.data.saved_file  }}"
      service: telegram_bot.send_photo
  alias: Object detection automation
  condition: []
  id: "1120092824622"
  trigger:
    - platform: event
      event_type: deepstack.object_detected
      event_data:
        name: person
```

## Displaying the deepstack latest jpg file
It easy to display the `deepstack_object_{source name}_latest.jpg` image with a [local_file](https://www.home-assistant.io/components/local_file/) camera. An example configuration is:
```yaml
camera:
  - platform: local_file
    file_path: /config/snapshots/deepstack_object_local_file_latest.jpg
    name: deepstack_latest_person
```

## Info on box
The `box` coordinates and the box center (`centroid`) can be used to determine whether an object falls within a defined region-of-interest (ROI). This can be useful to include/exclude objects by their location in the image.

* The `box` is defined by the tuple `(y_min, x_min, y_max, x_max)` (equivalent to image top, left, bottom, right) where the coordinates are floats in the range `[0.0, 1.0]` and relative to the width and height of the image.
* The centroid is in `(x,y)` coordinates where `(0,0)` is the top left hand corner of the image and `(1,1)` is the bottom right corner of the image.

## Browsing saved images in HA
I highly recommend using the Home Assistant Media Player Browser to browse and preview processed images. Add to your config something like:
```yaml
homeassistant:
.
.
  whitelist_external_dirs:
    - /config/images/
  media_dirs:
    local: /config/images/

media_source:
```
And configure Deepstack to use the above directory for `save_file_folder`, then saved images can be browsed from the HA front end like below:

<p align="center">
<img src="https://github.com/robmarkcole/HASS-Deepstack-object/blob/master/docs/media_player.png" width="750">
</p>

## Face recognition
For face recognition with Deepstack use https://github.com/robmarkcole/HASS-Deepstack-face

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

Q4: What are the minimum hardware requirements for running Deepstack?

A4. Based on my experience, I would allow 0.5 GB RAM per model.

------

Q5: Can object detection be configured to detect car/car colour?

A5: The list of detected object classes is at the end of the page [here](https://deepstackpython.readthedocs.io/en/latest/objectdetection.html). There is no support for detecting the colour of an object.

------

Q6: I am getting an error from Home Assistant: `Platform error: image_processing - Integration deepstack_object not found`

A6: This can happen when you are running in Docker/Hassio, and indicates that one of the dependencies isn't installed. It is necessary to reboot your Hassio device, or rebuild your Docker container. Note that just restarting Home Assistant will not resolve this.

------

## Objects
The following lists all valid target object names:
```
person,   bicycle,   car,   motorcycle,   airplane,
bus,   train,   truck,   boat,   traffic light,   fire hydrant,   stop_sign,
parking meter,   bench,   bird,   cat,   dog,   horse,   sheep,   cow,   elephant,
bear,   zebra, giraffe,   backpack,   umbrella,   handbag,   tie,   suitcase,
frisbee,   skis,   snowboard, sports ball,   kite,   baseball bat,   baseball glove,
skateboard,   surfboard,   tennis racket, bottle,   wine glass,   cup,   fork,
knife,   spoon,   bowl,   banana,   apple,   sandwich,   orange, broccoli,   carrot,
hot dog,   pizza,   donut,   cake,   chair,   couch,   potted plant,   bed, dining table,
toilet,   tv,   laptop,   mouse,   remote,   keyboard,   cell phone,   microwave,
oven,   toaster,   sink,   refrigerator,   book,   clock,   vase,   scissors,   teddy bear,
hair dryer, toothbrush.
```
Objects are grouped by the following `object_type`:
- **person**: person
- **animal**: bird, cat, dog, horse, sheep, cow, elephant, bear, zebra, giraffe
- **vehicle**: bicycle, car, motorcycle, airplane, bus, train, truck
- **other**: any object that is not in `person`, `animal` or `vehicle`

## Development
Currently only the helper functions are tested, using pytest.
* `python3 -m venv venv`
* `source venv/bin/activate`
* `pip install -r requirements-dev.txt`
* `venv/bin/py.test custom_components/deepstack_object/tests.py -vv -p no:warnings`
