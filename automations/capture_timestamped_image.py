"""
Capture a timestamped camera image using the service camera.snapshot. This script is triggered by the following automation:

  trigger:
  - entity_id: binary_sensor.hue_front_porch_motion_sensor
    from: 'off'
    platform: state
    to: 'on'
  condition:
  - after: sunrise
    before: sunset
    condition: sun
  action:
  - data: {}
    service: python_script.capture_timestamped_image
"""
BLINK_SLEEP_TIME = 7  # seconds to wait for Blink
HA_SLEEP_TIME = 3 # seconds to wait for HA
CAMERA_ENTITY_ID = 'camera.blink_living_room'
CAMERA_NAME = 'Living_room'
IMAGE_PROCESSING_ENTITY_ID = 'image_processing.deepstack_object_blink_living_room'

now = datetime.datetime.now()
time_str = "{}_{}_{}_{}_{}_{}_{}".format(
    now.year, now.month, now.day, now.hour,
    now.minute, now.second, now.microsecond)

# Trigger a capture now
hass.services.call(
    'blink', 'trigger_camera',
    {'name': CAMERA_NAME})
time.sleep(BLINK_SLEEP_TIME)

# Update representation in HA
hass.services.call(
    'blink', 'blink_update')
time.sleep(HA_SLEEP_TIME)

# Save using snapshot
folder = '/config/www/blink_{}_'.format(CAMERA_NAME)
filename = folder + time_str + '.jpg'

hass.services.call(
    'camera', 'snapshot',
    {'entity_id': CAMERA_ENTITY_ID,
     'filename': filename})

## Call image processing
hass.services.call(
    'image_processing', 'scan', {
        "entity_id": IMAGE_PROCESSING_ENTITY_ID
    })
