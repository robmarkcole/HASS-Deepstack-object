"""
Component that will perform object detection and identification via CodeProject.AI Server.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/image_processing.codeproject_ai_object
"""
from collections import namedtuple, Counter
import datetime
import io
import logging
import os
import re
from datetime import timedelta
from typing import Tuple, Dict, List
from pathlib import Path

from PIL import Image, ImageDraw, UnidentifiedImageError
import voluptuous as vol

import codeprojectai.core as cpai

import homeassistant.helpers.config_validation as cv
import homeassistant.util.dt as dt_util
from homeassistant.util.pil import draw_box
from homeassistant.components.image_processing import (
    ATTR_CONFIDENCE,
    CONF_CONFIDENCE,
    CONF_ENTITY_ID,
    CONF_NAME,
    CONF_SOURCE,
    DEFAULT_CONFIDENCE,
    DOMAIN,
    PLATFORM_SCHEMA,
    ImageProcessingEntity,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_NAME,
    CONF_IP_ADDRESS,
    CONF_PORT,
)
from homeassistant.core import split_entity_id

_LOGGER = logging.getLogger(__name__)

ANIMAL = "animal"
ANIMALS = [
    "bird",
    "cat",
    "dog",
    "horse",
    "sheep",
    "cow",
    "elephant",
    "bear",
    "zebra",
    "giraffe",
]
OTHER = "other"
PERSON = "person"
VEHICLE = "vehicle"
VEHICLES = ["bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck"]
OBJECT_TYPES = [ANIMAL, OTHER, PERSON, VEHICLE]


CONF_TARGET = "target"
CONF_TARGETS = "targets"
CONF_TIMEOUT = "timeout"
CONF_SAVE_FILE_FORMAT = "save_file_format"
CONF_SAVE_FILE_FOLDER = "save_file_folder"
CONF_SAVE_TIMESTAMPTED_FILE = "save_timestamped_file"
CONF_ALWAYS_SAVE_LATEST_FILE = "always_save_latest_file"
CONF_SHOW_BOXES = "show_boxes"
CONF_ROI_Y_MIN = "roi_y_min"
CONF_ROI_X_MIN = "roi_x_min"
CONF_ROI_Y_MAX = "roi_y_max"
CONF_ROI_X_MAX = "roi_x_max"
CONF_SCALE = "scale"
CONF_CUSTOM_MODEL = "custom_model"
CONF_CROP_ROI = "crop_to_roi"

DATETIME_FORMAT = "%Y-%m-%d_%H-%M-%S-%f"
DEFAULT_TARGETS = [{CONF_TARGET: PERSON}]
DEFAULT_TIMEOUT = 10
DEFAULT_ROI_Y_MIN = 0.0
DEFAULT_ROI_Y_MAX = 1.0
DEFAULT_ROI_X_MIN = 0.0
DEFAULT_ROI_X_MAX = 1.0
DEAULT_SCALE = 1.0
DEFAULT_ROI = (
    DEFAULT_ROI_Y_MIN,
    DEFAULT_ROI_X_MIN,
    DEFAULT_ROI_Y_MAX,
    DEFAULT_ROI_X_MAX,
)

EVENT_OBJECT_DETECTED = "codeproject_ai.object_detected"
BOX = "box"
FILE = "file"
OBJECT = "object"
SAVED_FILE = "saved_file"
MIN_CONFIDENCE = 0.1
JPG = "jpg"
PNG = "png"

# rgb(red, green, blue)
RED = (255, 0, 0)  # For objects within the ROI
GREEN = (0, 255, 0)  # For ROI box
YELLOW = (255, 255, 0)  # Unused

TARGETS_SCHEMA = {
    vol.Required(CONF_TARGET): cv.string,
    vol.Optional(CONF_CONFIDENCE): vol.All(
        vol.Coerce(float), vol.Range(min=10, max=100)
    ),
}


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_IP_ADDRESS): cv.string,
        vol.Required(CONF_PORT): cv.port,
        # vol.Optional(CONF_API_KEY, default=DEFAULT_API_KEY): cv.string,
        vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): cv.positive_int,
        vol.Optional(CONF_CUSTOM_MODEL, default=""): cv.string,
        vol.Optional(CONF_TARGETS, default=DEFAULT_TARGETS): vol.All(
            cv.ensure_list, [vol.Schema(TARGETS_SCHEMA)]
        ),
        vol.Optional(CONF_ROI_Y_MIN, default=DEFAULT_ROI_Y_MIN): cv.small_float,
        vol.Optional(CONF_ROI_X_MIN, default=DEFAULT_ROI_X_MIN): cv.small_float,
        vol.Optional(CONF_ROI_Y_MAX, default=DEFAULT_ROI_Y_MAX): cv.small_float,
        vol.Optional(CONF_ROI_X_MAX, default=DEFAULT_ROI_X_MAX): cv.small_float,
        vol.Optional(CONF_SCALE, default=DEAULT_SCALE): vol.All(
            vol.Coerce(float, vol.Range(min=0.1, max=1))
        ),
        vol.Optional(CONF_SAVE_FILE_FOLDER): cv.isdir,
        vol.Optional(CONF_SAVE_FILE_FORMAT, default=JPG): vol.In([JPG, PNG]),
        vol.Optional(CONF_SAVE_TIMESTAMPTED_FILE, default=False): cv.boolean,
        vol.Optional(CONF_ALWAYS_SAVE_LATEST_FILE, default=False): cv.boolean,
        vol.Optional(CONF_SHOW_BOXES, default=True): cv.boolean,
        vol.Optional(CONF_CROP_ROI, default=False): cv.boolean,
    }
)

Box = namedtuple("Box", "y_min x_min y_max x_max")
Point = namedtuple("Point", "y x")


def point_in_box(box: Box, point: Point) -> bool:
    """Return true if point lies in box"""
    if (box.x_min <= point.x <= box.x_max) and (box.y_min <= point.y <= box.y_max):
        return True
    return False


def object_in_roi(roi: dict, centroid: dict) -> bool:
    """Convenience to convert dicts to the Point and Box."""
    target_center_point = Point(centroid["y"], centroid["x"])
    roi_box = Box(roi["y_min"], roi["x_min"], roi["y_max"], roi["x_max"])
    return point_in_box(roi_box, target_center_point)


def get_valid_filename(name: str) -> str:
    return re.sub(r"(?u)[^-\w.]", "", str(name).strip().replace(" ", "_"))


def get_object_type(object_name: str) -> str:
    if object_name == PERSON:
        return PERSON
    elif object_name in ANIMALS:
        return ANIMAL
    elif object_name in VEHICLES:
        return VEHICLE
    else:
        return OTHER


def get_objects(predictions: list, img_width: int, img_height: int) -> List[Dict]:
    """Return objects with formatting and extra info."""
    objects = []
    decimal_places = 3
    for pred in predictions:
        box_width = pred["x_max"] - pred["x_min"]
        box_height = pred["y_max"] - pred["y_min"]
        box = {
            "height": round(box_height / img_height, decimal_places),
            "width": round(box_width / img_width, decimal_places),
            "y_min": round(pred["y_min"] / img_height, decimal_places),
            "x_min": round(pred["x_min"] / img_width, decimal_places),
            "y_max": round(pred["y_max"] / img_height, decimal_places),
            "x_max": round(pred["x_max"] / img_width, decimal_places),
        }
        box_area = round(box["height"] * box["width"], decimal_places)
        centroid = {
            "x": round(box["x_min"] + (box["width"] / 2), decimal_places),
            "y": round(box["y_min"] + (box["height"] / 2), decimal_places),
        }
        name = pred["label"]
        object_type = get_object_type(name)
        confidence = round(pred["confidence"] * 100, decimal_places)

        objects.append(
            {
                "bounding_box": box,
                "box_area": box_area,
                "centroid": centroid,
                "name": name,
                "object_type": object_type,
                "confidence": confidence,
            }
        )
    return objects


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the classifier."""
    save_file_folder = config.get(CONF_SAVE_FILE_FOLDER)
    if save_file_folder:
        save_file_folder = Path(save_file_folder)

    entities = []
    for camera in config[CONF_SOURCE]:
        object_entity = ObjectClassifyEntity(
            ip_address=config.get(CONF_IP_ADDRESS),
            port=config.get(CONF_PORT),
            timeout=config.get(CONF_TIMEOUT),
            custom_model=config.get(CONF_CUSTOM_MODEL),
            targets=config.get(CONF_TARGETS),
            confidence=config.get(CONF_CONFIDENCE),
            roi_y_min=config[CONF_ROI_Y_MIN],
            roi_x_min=config[CONF_ROI_X_MIN],
            roi_y_max=config[CONF_ROI_Y_MAX],
            roi_x_max=config[CONF_ROI_X_MAX],
            scale=config[CONF_SCALE],
            show_boxes=config[CONF_SHOW_BOXES],
            save_file_folder=save_file_folder,
            save_file_format=config[CONF_SAVE_FILE_FORMAT],
            save_timestamped_file=config.get(CONF_SAVE_TIMESTAMPTED_FILE),
            always_save_latest_file=config.get(CONF_ALWAYS_SAVE_LATEST_FILE),
            crop_roi=config[CONF_CROP_ROI],
            camera_entity=camera.get(CONF_ENTITY_ID),
            name=camera.get(CONF_NAME),
        )
        entities.append(object_entity)
    add_devices(entities)


class ObjectClassifyEntity(ImageProcessingEntity):
    """Perform a object classification."""

    def __init__(
        self,
        ip_address,
        port,
        timeout,
        custom_model,
        targets,
        confidence,
        roi_y_min,
        roi_x_min,
        roi_y_max,
        roi_x_max,
        scale,
        show_boxes,
        save_file_folder,
        save_file_format,
        save_timestamped_file,
        always_save_latest_file,
        crop_roi,
        camera_entity,
        name=None,
    ):
        """Init with the API key and model id."""
        super().__init__()
        self._cpai_object = cpai.CodeProjectAIObject(
            ip=ip_address,
            port=port,
            timeout=timeout,
            min_confidence=MIN_CONFIDENCE,
            custom_model=custom_model,
        )
        self._custom_model = custom_model
        self._confidence = confidence
        self._summary = {}
        self._targets = targets
        for target in self._targets:
            if CONF_CONFIDENCE not in target.keys():
                target.update({CONF_CONFIDENCE: self._confidence})
        self._targets_names = [
            target[CONF_TARGET] for target in targets
        ]  # can be a name or a type
        self._camera = camera_entity
        if name:
            self._name = name
        else:
            camera_name = split_entity_id(camera_entity)[1]
            self._name = "codeproject_ai_object_{}".format(camera_name)

        self._state = None
        self._objects = []  # The parsed raw data
        self._targets_found = []
        self._last_detection = None

        self._roi_dict = {
            "y_min": roi_y_min,
            "x_min": roi_x_min,
            "y_max": roi_y_max,
            "x_max": roi_x_max,
        }
        self._crop_roi = crop_roi
        self._scale = scale
        self._show_boxes = show_boxes
        self._image_width = None
        self._image_height = None
        self._save_file_folder = save_file_folder
        self._save_file_format = save_file_format
        self._always_save_latest_file = always_save_latest_file
        self._save_timestamped_file = save_timestamped_file
        self._always_save_latest_file = always_save_latest_file
        self._image = None

    def process_image(self, image):
        """Process an image."""
        self._image = Image.open(io.BytesIO(bytearray(image)))
        self._image_width, self._image_height = self._image.size
        # scale to roi
        if self._crop_roi:
            roi = (
                self._image_width * self._roi_dict["x_min"],
                self._image_height * self._roi_dict["y_min"],
                self._image_width * (self._roi_dict["x_max"]),
                self._image_height * (self._roi_dict["y_max"])
            )
            self._image = self._image.crop(roi)
            self._image_width, self._image_height = self._image.size
            with io.BytesIO() as output:
                self._image.save(output, format="JPEG")
                image = output.getvalue()
            _LOGGER.debug(
                (
                    f"Image cropped with : {self._roi_dict} W={self._image_width} H={self._image_height}"
                )
            )
        # resize image if different then default
        if self._scale != DEAULT_SCALE:
            newsize = (self._image_width * self._scale, self._image_width * self._scale)
            self._image.thumbnail(newsize, Image.ANTIALIAS)
            self._image_width, self._image_height = self._image.size
            with io.BytesIO() as output:
                self._image.save(output, format="JPEG")
                image = output.getvalue()
            _LOGGER.debug(
                (
                    f"Image scaled with : {self._scale} W={self._image_width} H={self._image_height}"
                )
            )

        self._state = None
        self._objects = []  # The parsed raw data
        self._targets_found = []
        self._summary = {}
        saved_image_path = None

        try:
            predictions = self._cpai_object.detect(image)
        except cpai.CodeProjectAIServerException as exc:
            _LOGGER.error("CodeProject.AI Server error : %s", exc)
            return

        self._objects = get_objects(predictions, self._image_width, self._image_height)
        self._targets_found = []

        for obj in self._objects:
            if not (
                (obj["name"] in self._targets_names)
                or (obj["object_type"] in self._targets_names)
            ):
                continue
            ## Then check if the type has a configured confidence, if yes assign
            ## Then if a confidence for a named object, this takes precedence over type confidence
            confidence = None
            for target in self._targets:
                if obj["object_type"] == target[CONF_TARGET]:
                    confidence = target[CONF_CONFIDENCE]
            for target in self._targets:
                if obj["name"] == target[CONF_TARGET]:
                    confidence = target[CONF_CONFIDENCE]
            if obj["confidence"] > confidence:
                if not self._crop_roi and not object_in_roi(self._roi_dict, obj["centroid"]):
                    continue
                self._targets_found.append(obj)

        self._state = len(self._targets_found)
        if self._state > 0:
            self._last_detection = dt_util.now().strftime(DATETIME_FORMAT)

        targets_found = [
            obj["name"] for obj in self._targets_found
        ]  # Just the list of target names, e.g. [car, car, person]
        self._summary = dict(Counter(targets_found))  # e.g. {'car':2, 'person':1}

        if self._save_file_folder:
            if self._state > 0 or self._always_save_latest_file:
                saved_image_path = self.save_image(
                    self._targets_found,
                    self._save_file_folder,
                )

        # Fire events
        for target in self._targets_found:
            target_event_data = target.copy()
            target_event_data[ATTR_ENTITY_ID] = self.entity_id
            if saved_image_path:
                target_event_data[SAVED_FILE] = saved_image_path
            self.hass.bus.fire(EVENT_OBJECT_DETECTED, target_event_data)

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
        return "targets"

    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def extra_state_attributes(self) -> Dict:
        """Return device specific state attributes."""
        attr = {}
        attr["targets"] = self._targets
        attr["targets_found"] = [
            {obj["name"]: obj["confidence"]} for obj in self._targets_found
        ]
        attr["summary"] = self._summary
        if self._last_detection:
            attr["last_target_detection"] = self._last_detection
        if self._custom_model:
            attr["custom_model"] = self._custom_model
        attr["all_objects"] = [
            {obj["name"]: obj["confidence"]} for obj in self._objects
        ]
        if self._save_file_folder:
            attr[CONF_SAVE_FILE_FOLDER] = str(self._save_file_folder)
            attr[CONF_SAVE_FILE_FORMAT] = self._save_file_format
            attr[CONF_SAVE_TIMESTAMPTED_FILE] = self._save_timestamped_file
            attr[CONF_ALWAYS_SAVE_LATEST_FILE] = self._always_save_latest_file
        return attr

    def save_image(self, targets, directory) -> str:
        """Draws the actual bounding box of the detected objects.

        Returns: saved_image_path, which is the path to the saved timestamped file if configured, else the default saved image.
        """
        try:
            img = self._image.convert("RGB")
        except UnidentifiedImageError:
            _LOGGER.warning("CodeProject.AI Server unable to process image, bad data")
            return
        draw = ImageDraw.Draw(img)

        roi_tuple = tuple(self._roi_dict.values())
        if roi_tuple != DEFAULT_ROI and self._show_boxes and not self._crop_roi:
            draw_box(
                draw,
                roi_tuple,
                img.width,
                img.height,
                text="ROI",
                color=GREEN,
            )

        for obj in targets:
            if not self._show_boxes:
                break
            name = obj["name"]
            confidence = obj["confidence"]
            box = obj["bounding_box"]
            centroid = obj["centroid"]
            box_label = f"{name}: {confidence:.1f}%"

            draw_box(
                draw,
                (box["y_min"], box["x_min"], box["y_max"], box["x_max"]),
                img.width,
                img.height,
                text=box_label,
                color=RED,
            )

            # draw bullseye
            draw.text(
                (centroid["x"] * img.width, centroid["y"] * img.height),
                text="X",
                fill=RED,
            )

        # Save images, returning the path of saved image as str
        latest_save_path = (
            directory
            / f"{get_valid_filename(self._name).lower()}_latest.{self._save_file_format}"
        )
        img.save(latest_save_path)
        _LOGGER.info("CodeProject.AI saved file %s", latest_save_path)
        saved_image_path = latest_save_path

        if self._save_timestamped_file:
            timestamp_save_path = (
                directory
                / f"{self._name}_{self._last_detection}.{self._save_file_format}"
            )
            img.save(timestamp_save_path)
            _LOGGER.info("CodeProject.AI saved file %s", timestamp_save_path)
            saved_image_path = timestamp_save_path
        return str(saved_image_path)
