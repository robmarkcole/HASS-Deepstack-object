# HASS-Deepstack
[Home Assistant](https://www.home-assistant.io/) custom component for using Deepstack face recognition &amp; object detection.

[Deepstack](https://www.deepquestai.com/insider/) is a service which runs in a docker container and exposes deep-learning models for performing facial recognition and object detection. There is no cost for using Deepstack, although you will need a machine with 8 GB RAM.

## Setup Deepstack
On your machine with docker, pull the latest image (approx. 2GB):
```
sudo docker pull deepquestai/deepstack
```

Run Deepstack with the face recognition service active run:
```
sudo docker run -e VISION-FACE=True -v localstorage:/datastore -p 5000:5000 deepquestai/deepstack
```

This will expose the service on port `5000`.

**GPU users** Note that if your machine has an Nvidia GPU you can get a 5 x 20 times performance boost by using the GPU, [read the docs here](https://deepstackpython.readthedocs.io/en/latest/gpuinstall.html#gpuinstall).

## Configure Home Assistant

Place the `custom_components` folder in your configuration directory (or add its contents to an existing `custom_components` folder).

Add to your Home-Assistant config:
