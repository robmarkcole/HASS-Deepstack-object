"""
Component that will perform facial detection and identification via deepstack.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/image_processing.deepstack_face
"""
import base64
import logging

import requests
import voluptuous as vol

from homeassistant.const import (
    ATTR_ENTITY_ID, ATTR_NAME)
from homeassistant.core import split_entity_id
import homeassistant.helpers.config_validation as cv
from homeassistant.components.image_processing import (
    PLATFORM_SCHEMA, ImageProcessingFaceEntity, ATTR_CONFIDENCE, CONF_SOURCE,
    CONF_ENTITY_ID, CONF_NAME, DOMAIN)
from homeassistant.const import (
    CONF_IP_ADDRESS, CONF_PORT,
    HTTP_BAD_REQUEST, HTTP_OK, HTTP_UNAUTHORIZED)

_LOGGER = logging.getLogger(__name__)

CLASSIFIER = 'deepstack'


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_IP_ADDRESS): cv.string,
    vol.Required(CONF_PORT): cv.port,
})


def get_genders(predictions):
    """
    Get the genders of predictions.
    """
    males = len([face for face in predictions if face['gender'] == 'male'])
    females = len([face for face in predictions if face['gender'] == 'female'])
    return {'males': males, 'females': females}


def post_image(url, image):
    """Post an image to the classifier."""
    try:
        response = requests.post(
            url,
            files={"image": image},
            )
        return response
    except requests.exceptions.ConnectionError:
        _LOGGER.error("ConnectionError: Is %s running?", CLASSIFIER)
        return None


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the classifier."""
    ip_address = config[CONF_IP_ADDRESS]
    port = config[CONF_PORT]
    entities = []
    for camera in config[CONF_SOURCE]:
        face_entity = FaceClassifyEntity(
            ip_address, port, camera[CONF_ENTITY_ID], camera.get(CONF_NAME))
        entities.append(face_entity)

    add_devices(entities)


class FaceClassifyEntity(ImageProcessingFaceEntity):
    """Perform a face classification."""

    def __init__(self, ip_address, port, camera_entity, name=None):
        """Init with the API key and model id."""
        super().__init__()
        self._url_check = "http://{}:{}/v1/vision/face".format(
            ip_address, port)
        self._camera = camera_entity
        if name:
            self._name = name
        else:
            camera_name = split_entity_id(camera_entity)[1]
            self._name = "{} {}".format(CLASSIFIER, camera_name)
        self.predictions = {}

    def process_image(self, image):
        """Process an image."""
        response = post_image(
            self._url_check, image)
        if response:
            if response.status_code == HTTP_OK:
                predictions_json = response.json()["predictions"]
                self.predictions = get_genders(predictions_json)
                self.total_faces = len(predictions_json)
        else:
            self.total_faces = None
            self.predictions = {}

    @property
    def camera_entity(self):
        """Return camera entity id from process pictures."""
        return self._camera

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def device_state_attributes(self):
        """Return the classifier attributes."""
        return self.predictions

