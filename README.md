# HASS-Deepstack
[Home Assistant](https://www.home-assistant.io/) custom component for using Deepstack face recognition &amp; object detection. The component adds an `image_processing` entity where the state of the entity is the total number of faces that are found in the camera image.

[Deepstack](https://www.deepquestai.com/insider/) is a service which runs in a docker container and exposes deep-learning models for performing facial recognition and object detection. There is no cost for using Deepstack, although you will need a machine with 8 GB RAM.

## Setup Deepstack
On your machine with docker, pull the latest image (approx. 2GB):
```
sudo docker pull deepquestai/deepstack
```

Run Deepstack with the face recognition service active:
```
sudo docker run -e VISION-FACE=True -v localstorage:/datastore -p 5000:5000 deepquestai/deepstack
```

This will expose the service on port `5000`.

**GPU users** Note that if your machine has an Nvidia GPU you can get a 5 x 20 times performance boost by using the GPU, [read the docs here](https://deepstackpython.readthedocs.io/en/latest/gpuinstall.html#gpuinstall).

## Configure Home Assistant

Place the `custom_components` folder in your configuration directory (or add its contents to an existing `custom_components` folder).

Add to your Home-Assistant config:
```yaml
image_processing:
  - platform: deepstack_face
    ip_address: localhost
    port: 5000
    source:
      - entity_id: camera.local_file
        name: my_deepstack_name
```
Configuration variables:
- **ip_address**: the ip address of your deepstack instance.
- **port**: the port of your deepstack instance.
- **source**: Must be a camera.
- **name**: (Optional) A custom name for the the entity.

### FAQ
Q1: I get the following warning, is this normal?
```
2019-01-15 06:37:52 WARNING (MainThread) [homeassistant.loader] You are using a custom component for image_processing.deepstack_face which has not been tested by Home Assistant. This component might cause stability problems, be sure to disable it if you do experience issues with Home Assistant.
```
A1: Yes this is normal
