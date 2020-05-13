"""The tests for the Deepstack object component."""
from .image_processing import get_objects

TARGET = "person"
IMG_WIDTH = 960
IMG_HEIGHT = 640

MOCK_PREDICTIONS = [
    {
        "confidence": 0.9995428,
        "label": "person",
        "y_min": 95,
        "x_min": 295,
        "y_max": 523,
        "x_max": 451,
    },
    {
        "confidence": 0.9994912,
        "label": "person",
        "y_min": 99,
        "x_min": 440,
        "y_max": 531,
        "x_max": 608,
    },
    {
        "confidence": 0.9990447,
        "label": "dog",
        "y_min": 358,
        "x_min": 647,
        "y_max": 539,
        "x_max": 797,
    },
]

PARSED_PREDICTIONS = [
    {
        "bounding_box": {
            "height": 0.669,
            "width": 0.163,
            "y_min": 0.148,
            "x_min": 0.307,
            "y_max": 0.817,
            "x_max": 0.47,
        },
        "box_area": 0.109,
        "centroid": {"x": 0.389, "y": 0.483},
        "name": "person",
        "confidence": 99.954,
    },
    {
        "bounding_box": {
            "height": 0.675,
            "width": 0.175,
            "y_min": 0.155,
            "x_min": 0.458,
            "y_max": 0.83,
            "x_max": 0.633,
        },
        "box_area": 0.118,
        "centroid": {"x": 0.545, "y": 0.493},
        "name": "person",
        "confidence": 99.949,
    },
    {
        "bounding_box": {
            "height": 0.283,
            "width": 0.156,
            "y_min": 0.559,
            "x_min": 0.674,
            "y_max": 0.842,
            "x_max": 0.83,
        },
        "box_area": 0.044,
        "centroid": {"x": 0.752, "y": 0.701},
        "name": "dog",
        "confidence": 99.904,
    },
]


def test_get_objects():
    objects = get_objects(MOCK_PREDICTIONS, IMG_WIDTH, IMG_HEIGHT)
    assert len(objects) == 3
    assert objects[0] == PARSED_PREDICTIONS[0]
