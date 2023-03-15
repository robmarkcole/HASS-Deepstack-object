# CodeProject.AI Home Assistant Object Detection custom component

This component is a direct port of the [HASS-Deepstack-object](https://github.com/robmarkcole/HASS-Deepstack-object) component by [Robin Cole](https://github.com/robmarkcole). This component provides AI-based Object Detection capabilities using [CodeProject.AI Server](https://codeproject.com/ai). 

 [CodeProject.AI Server](https://codeproject.com/ai) is a service which runs either in a Docker container or as a Windows Service and exposes various an API for many AI inferencing operations via a REST API. The Object Detection capabilities use the [YOLO](https://arxiv.org/pdf/1506.02640.pdf) algorithm as implemented by Ultralytics and others. It can identify 80 different kinds of objects by default, but custom models are also available that focus on specific objects such as animals, license plates or objects typically encountered by home webcams. CodeProject.AI Server is free, locally installed, and can run without an external internet connection, is is comatible with Windows, Linux, macOS. It can run on Raspberry Pi, and supports CUDA and embedded Intel GPUs.

On the machine in which you are running CodeProject.AI server, either ensure the service is running, or if using Docker, [start a Docker container](https://www.codeproject.com/ai/docs/why/running_in_docker.html#launching-a-container). 

### A note on Ports
CodeProject.AI Server typically runs on port 32168, so you will need to ensure the machine hosting the server has this port open. If you need to changes ports (eg switch to port 80) thenf or Docker use the -p flag:
```
docker run --name CodeProject.AI-Server -d -p 80:32168 ^
 --mount type=bind,source=C:\ProgramData\CodeProject\AI\docker\data,target=/etc/codeproject/ai ^
 --mount type=bind,source=C:\ProgramData\CodeProject\AI\docker\modules,target=/app/modules ^
   codeproject/ai-server
```
For Windows server you will need to either set an environment variable `CPAI_PORT` with value 80 (on the host running CodeProject.AI Server), or edit the appsettings.json file in the `C:\Program Files\CodeProject\AI folder` and change the value of the CPAI_PORT environment variable in the file.

## Usage of this component
Thanks again to Robin for the original write up for his component.

The `codeproject_ai_object` component adds an `image_processing` entity where the state of the entity is the total count of target objects that are above a `confidence` threshold which has a default value of 80%. You can have a single target object class, or multiple. The time of the last detection of any target object is in the `last target detection` attribute. The type and number of objects (of any confidence) is listed in the `summary` attributes. Optionally a region of interest (ROI) can be configured, and only objects with their center (represented by a `x`) within the ROI will be included in the state count. The ROI will be displayed as a green box, and objects with their center in the ROI have a red box.

Also optionally the processed image can be saved to disk, with bounding boxes showing the location of detected objects. If `save_file_folder` is configured, an image with filename of format `codeproject_ai_object_{source name}_latest.jpg` is over-written on each new detection of a target. Optionally this image can also be saved with a timestamp in the filename, if `save_timestamped_file` is configured as `True`. An event `codeproject_ai.object_detected` is fired for each object detected that is in the targets list, and meets the confidence and ROI criteria. If you are a power user with advanced needs such as zoning detections or you want to track multiple object types, you will need to use the `codeproject_ai.object_detected` events.

**Note** that by default the component will **not** automatically scan images, but requires you to call the `image_processing.scan` service e.g. using an automation triggered by motion.

## Home Assistant setup
Place the `custom_components` folder in your configuration directory (or add its contents to an existing `custom_components` folder). Then configure object detection. **Important:** It is necessary to configure only a single camera per `codeproject_ai_object` entity. If you want to process multiple cameras, you will therefore need multiple `codeproject_ai_object` `image_processing` entities.

The component can optionally save snapshots of the processed images. If you would like to use this option, you need to create a folder where the snapshots will be stored. The folder should be in the same folder where your `configuration.yaml` file is located. In the example below, we have named the folder `snapshots`.

Add to your Home-Assistant config:

```yaml
image_processing:
  - platform: codeproject_ai_object
    ip_address: localhost
    port: 32168
    # custom_model: mask
    # confidence: 80
    save_file_folder: /config/snapshots/
    save_file_format: png
    save_timestamped_file: True
    always_save_latest_file: True
    scale: 0.75
    # roi_x_min: 0.35
    roi_x_max: 0.8
    #roi_y_min: 0.4
    roi_y_max: 0.8
    crop_to_roi: True
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
- **ip_address**: the ip address of your CodeProject.AI Server instance.
- **port**: the port of your CodeProject.AI Server instance.
- **timeout**: (Optional, default 10 seconds) The timeout for requests to CodeProject.AI Server.
- **custom_model**: (Optional) The name of a custom model if you are using one. Don't forget to add the targets from the custom model below
- **confidence**: (Optional) The confidence (in %) above which detected targets are counted in the sensor state. Default value: 80
- **save_file_folder**: (Optional) The folder to save processed images to. Note that folder path should be added to [whitelist_external_dirs](https://www.home-assistant.io/docs/configuration/basic/)
- **save_file_format**: (Optional, default `jpg`, alternatively `png`) The file format to save images as. `png` generally results in easier to read annotations.
- **save_timestamped_file**: (Optional, default `False`, requires `save_file_folder` to be configured) Save the processed image with the time of detection in the filename.
- **always_save_latest_file**: (Optional, default `False`, requires `save_file_folder` to be configured) Always save the last processed image, even if there were no detections.
- **scale**: (optional, default 1.0), range 0.1-1.0, applies a scaling factor to the images that are saved. This reduces the disk space used by saved images, and is especially beneficial when using high resolution cameras.
- **show_boxes**: (optional, default `True`), if `False` bounding boxes are not shown on saved images
- **roi_x_min**: (optional, default 0), range 0-1, must be less than roi_x_max
- **roi_x_max**: (optional, default 1), range 0-1, must be more than roi_x_min
- **roi_y_min**: (optional, default 0), range 0-1, must be less than roi_y_max
- **roi_y_max**: (optional, default 1), range 0-1, must be more than roi_y_min
- **crop_to_roi**: (optional, default False), crops the image to the specified roi.  May improve object detection accuracy when a region-of-interest is applied
- **source**: Must be a camera.
- **targets**: The list of target object names and/or `object_type`, default `person`. Optionally a `confidence` can be set for this target, if not the default confidence is used. Note the minimum possible confidence is 10%.

For the ROI, the (x=0,y=0) position is the top left pixel of the image, and the (x=1,y=1) position is the bottom right pixel of the image. It might seem a bit odd to have y running from top to bottom of the image, but that is the coordinate system used by pillow.

#### Event `codeproject_ai.object_detected`
An event `codeproject_ai.object_detected` is fired for each object detected above the configured `confidence` threshold. This is the recommended way to check the confidence of detections, and to keep track of objects that are not configured as the `target` (use `Developer tools -> EVENTS -> :Listen to events`, to monitor these events). 

An example use case for event is to get an alert when some rarely appearing object is detected, or to increment a [counter](https://www.home-assistant.io/components/counter/). The `codeproject_ai.object_detected` event payload includes:

- `entity_id` : the entity id responsible for the event
- `name` : the name of the object detected
- `object_type` : the type of the object, from `person`, `vehicle`, `animal` or `other`
- `confidence` : the confidence in detection in the range 0 - 100%
- `box` : the bounding box of the object
- `centroid` : the centre point of the object
- `saved_file` : the path to the saved annotated image, which is the timestamped file if `save_timestamped_file` is True, or the default saved image if False

An example automation using the `codeproject_ai.object_detected` event is given below:

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
      event_type: codeproject_ai.object_detected
      event_data:
        name: person
```

## Displaying the CodeProject.AI latest jpg file
It easy to display the `codeproject_ai_object_{source name}_latest.jpg` image with a [local_file](https://www.home-assistant.io/components/local_file/) camera. An example configuration is:
```yaml
camera:
  - platform: local_file
    file_path: /config/snapshots/codeproject_ai_object_local_file_latest.jpg
    name: codeproject_ai_latest_person
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
And configure CodeProject.AI Server to use the above directory for `save_file_folder`, then saved images can be browsed from the HA front end like below:

<p align="center">
<img src="https://github.com/robmarkcole/HASS-Deepstack-object/blob/master/docs/media_player.png" width="750">

<small>(Image courtesy of Robin Cole, and uses his original Deepstack implementation)</small>
</p>

## Face recognition
For face recognition with CodeProject.AI Server use https://github.com/codeproject/CodeProject.AI-HomeAssist-FaceDetect

### Support
 - For code related issues such as suspected bugs **with this integration**, please open an issue on this repo.
 - For CodeProject.AI Server setup questions, please see see the [CodeProject.AI Server docs](https://www.codeproject.com/AI/docs/)
 - For bugs and suggestions related to CodeProject.AI Server, please use the [CodeProject.AI forum](https://www.codeproject.com/Feature/CodeProjectAI-Discussions.aspx). 
 - For general chat or to discuss Home Assistant specific issues related to configuration or use cases, please [use the Home Assistant forums](https://community.home-assistant.io/).

### Docker tips

Please view the [CodeProject.AI Server docs](https://www.codeproject.com/AI/docs/why/running_in_docker.html)
Add the `-d` flag to run the container in background

### FAQ
Q1: I get the following warning, is this normal?
```
2019-01-15 06:37:52 WARNING (MainThread) [homeassistant.loader] You are using a custom component for image_processing.codeproject_ai_face which has not been tested by Home Assistant. This component might cause stability problems, be sure to disable it if you do experience issues with Home Assistant.
```
A1: Yes this is normal

------

Q6: I am getting an error from Home Assistant: `Platform error: image_processing - Integration codeproject_ai_object not found`

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
* `venv/bin/py.test custom_components/codeproject_ai_object/tests.py -vv -p no:warnings`

## Videos of usage

Robin Cole has a series of videos using Deepstack with Home Asssistant which may provide some assistance.

Checkout this excellent video of usage from [Everything Smart Home](https://www.youtube.com/channel/UCrVLgIniVg6jW38uVqDRIiQ)

[![](http://img.youtube.com/vi/vMdpLiAB9dI/0.jpg)](http://www.youtube.com/watch?v=vMdpLiAB9dI "")

Also see the video of a presentation I did to the [IceVision](https://airctic.com/) community on deploying Deepstack on a Jetson nano.

[![](http://img.youtube.com/vi/1O0mCaA22fE/0.jpg)](http://www.youtube.com/watch?v=1O0mCaA22fE "")
