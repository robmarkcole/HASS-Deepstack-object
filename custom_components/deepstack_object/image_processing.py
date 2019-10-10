"""
Component that will perform object detection and identification via deepstack.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/image_processing.deepstack_object
"""
import base64
import datetime
import io
from typing import Tuple
import json
import logging
import os

from PIL import Image, ImageDraw

import requests
import voluptuous as vol

import deepstack.core as ds

import homeassistant.util.dt as dt_util
from homeassistant.const import ATTR_ENTITY_ID, ATTR_NAME
from homeassistant.core import split_entity_id
import homeassistant.helpers.config_validation as cv
from homeassistant.components.image_processing import (
    PLATFORM_SCHEMA,
    ImageProcessingEntity,
    ATTR_CONFIDENCE,
    CONF_SOURCE,
    CONF_ENTITY_ID,
    CONF_NAME,
    DOMAIN,
)
from homeassistant.const import (
    CONF_IP_ADDRESS,
    CONF_PORT,
    HTTP_BAD_REQUEST,
    HTTP_OK,
    HTTP_UNAUTHORIZED,
)

_LOGGER = logging.getLogger(__name__)

CONF_API_KEY = "api_key"
CONF_TARGET = "target"
CONF_TIMEOUT = "timeout"
CONF_SAVE_FILE_FOLDER = "save_file_folder"
DEFAULT_API_KEY = ""
DEFAULT_TARGET = "person"
DEFAULT_TIMEOUT = 10
EVENT_OBJECT_DETECTED = "image_processing.object_detected"
EVENT_FILE_SAVED = "image_processing.file_saved"
FILE = "file"
OBJECT = "object"


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_IP_ADDRESS): cv.string,
        vol.Required(CONF_PORT): cv.port,
        vol.Optional(CONF_API_KEY, default=DEFAULT_API_KEY): cv.string,
        vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): cv.positive_int,
        vol.Optional(CONF_TARGET, default=DEFAULT_TARGET): cv.string,
        vol.Optional(CONF_SAVE_FILE_FOLDER): cv.isdir,
    }
)


def get_box(prediction: dict, img_width: int, img_height: int):
    """
    Return the relative bounxing box coordinates
    defined by the tuple (y_min, x_min, y_max, x_max)
    where the coordinates are floats in the range [0.0, 1.0] and
    relative to the width and height of the image.
    """
    box = [
        prediction["y_min"] / img_height,
        prediction["x_min"] / img_width,
        prediction["y_max"] / img_height,
        prediction["x_max"] / img_width,
    ]

    rounding_decimals = 3
    box = [round(coord, rounding_decimals) for coord in box]
    return box


def draw_box(
    draw: ImageDraw,
    box: Tuple[float, float, float, float],
    img_width: int,
    img_height: int,
    text: str = "",
    color: Tuple[int, int, int] = (255, 255, 0),
) -> None:
    """
    Draw a bounding box on and image.
    The bounding box is defined by the tuple (y_min, x_min, y_max, x_max)
    where the coordinates are floats in the range [0.0, 1.0] and
    relative to the width and height of the image.
    For example, if an image is 100 x 200 pixels (height x width) and the bounding
    box is `(0.1, 0.2, 0.5, 0.9)`, the upper-left and bottom-right coordinates of
    the bounding box will be `(40, 10)` to `(180, 50)` (in (x,y) coordinates).
    """

    line_width = 5
    y_min, x_min, y_max, x_max = box
    (left, right, top, bottom) = (
        x_min * img_width,
        x_max * img_width,
        y_min * img_height,
        y_max * img_height,
    )
    draw.line(
        [(left, top), (left, bottom), (right, bottom), (right, top), (left, top)],
        width=line_width,
        fill=color,
    )
    if text:
        draw.text((left + line_width, abs(top - line_width)), text, fill=color)


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the classifier."""
    ip_address = config.get(CONF_IP_ADDRESS)
    port = config.get(CONF_PORT)
    api_key = config.get(CONF_API_KEY)
    timeout = config.get(CONF_TIMEOUT)
    target = config.get(CONF_TARGET)
    save_file_folder = config.get(CONF_SAVE_FILE_FOLDER)
    confidence = config.get(ATTR_CONFIDENCE)

    if save_file_folder:
        save_file_folder = os.path.join(save_file_folder, "")  # If no trailing / add it

    entities = []
    for camera in config[CONF_SOURCE]:
        object_entity = ObjectClassifyEntity(
            ip_address,
            port,
            api_key,
            timeout,
            target,
            confidence,
            save_file_folder,
            camera[CONF_ENTITY_ID],
            camera.get(CONF_NAME),
        )
        entities.append(object_entity)
    add_devices(entities)


class ObjectClassifyEntity(ImageProcessingEntity):
    """Perform a face classification."""

    def __init__(
        self,
        ip_address,
        port,
        api_key,
        timeout,
        target,
        confidence,
        save_file_folder,
        camera_entity,
        name=None,
    ):
        """Init with the API key and model id."""
        super().__init__()
        self._dsobject = ds.DeepstackObject(ip_address, port, api_key, timeout)
        self._target = target
        self._confidence = confidence
        self._camera = camera_entity
        if name:
            self._name = name
        else:
            camera_name = split_entity_id(camera_entity)[1]
            self._name = "{} {}".format(CLASSIFIER, camera_name)
        self._state = None
        self._targets_confidences = []
        self._predictions = {}
        self._summary = {}
        self._last_detection = None
        self._image_width = None
        self._image_height = None
        if save_file_folder:
            self._save_file_folder = save_file_folder

    def process_image(self, image):
        """Process an image."""
        self._image_width, self._image_height = Image.open(
            io.BytesIO(bytearray(image))
        ).size
        self._state = None
        self._targets_confidences = []
        self._predictions = {}
        self._summary = {}
        try:
            self._dsobject.detect(image)
        except ds.DeepstackException as exc:
            _LOGGER.error("Depstack error : %s", exc)
            return

        self._predictions = self._dsobject.predictions.copy()

        if len(self._predictions) > 0:
            raw_confidences = ds.get_object_confidences(self._predictions, self._target)
            self._targets_confidences = [
                ds.format_confidence(confidence) for confidence in raw_confidences
            ]
            self._state = len(
                ds.get_confidences_above_threshold(
                    self._targets_confidences, self._confidence
                )
            )
            if self._state > 0:
                self._last_detection = dt_util.now()
            self._summary = ds.get_objects_summary(self._predictions)
            self.fire_prediction_events(self._predictions, self._confidence)
            if hasattr(self, "_save_file_folder") and self._state > 0:
                self.save_image(
                    image, self._predictions, self._target, self._save_file_folder
                )

    def save_image(self, image, predictions, target, directory):
        """Save a timestamped image with bounding boxes around targets."""

        img = Image.open(io.BytesIO(bytearray(image))).convert("RGB")
        draw = ImageDraw.Draw(img)

        for prediction in predictions:
            prediction_confidence = ds.format_confidence(prediction["confidence"])
            if (
                prediction["label"] == target
                and prediction_confidence >= self._confidence
            ):
                box = get_box(prediction, self._image_width, self._image_height)
                draw_box(
                    draw,
                    box,
                    self._image_width,
                    self._image_height,
                    str(prediction_confidence),
                )

        latest_save_path = directory + "deepstack_latest_{}.jpg".format(target)
        timestamp_save_path = directory + "deepstack_{}_{}.jpg".format(
            target, self._last_detection.strftime("%Y-%m-%d-%H-%M-%S")
        )
        try:
            img.save(latest_save_path)
            img.save(timestamp_save_path)
            self.fire_saved_file_event(timestamp_save_path)
            _LOGGER.info("Saved bounding box image to %s", timestamp_save_path)
        except Exception as exc:
            _LOGGER.error("Error saving bounding box image : %s", exc)

    def fire_prediction_events(self, predictions, confidence):
        """Fire events based on predictions if above confidence threshold."""

        for prediction in predictions:
            if ds.format_confidence(prediction["confidence"]) > confidence:
                self.hass.bus.fire(
                    EVENT_OBJECT_DETECTED,
                    {
                        ATTR_ENTITY_ID: self.entity_id,
                        OBJECT: prediction["label"],
                        ATTR_CONFIDENCE: ds.format_confidence(prediction["confidence"]),
                    },
                )

    def fire_saved_file_event(self, save_path):
        """Fire event when saving a file"""
        self.hass.bus.fire(
            EVENT_FILE_SAVED, {ATTR_ENTITY_ID: self.entity_id, FILE: save_path}
        )

    @property
    def camera_entity(self):
        """Return camera entity id from process pictures."""
        return self._camera

    @property
    def state(self):
        """Return the state of the entity."""
        return self._state

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        target = self._target
        if self._state != None and self._state > 1:
            target += "s"
        return target

    @property
    def device_state_attributes(self):
        """Return device specific state attributes."""
        attr = {}
        attr["target"] = self._target
        if self._last_detection:
            attr["last_detection"] = self._last_detection.strftime("%Y-%m-%d %H:%M:%S")
        attr["summary"] = self._summary
        return attr
