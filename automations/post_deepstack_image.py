"""
Pass file_path into this script with automation:

- action:
  - data_template: 
      file_path: "{{ trigger.event.data.file }}"
    service: python_script.process_deepstack_image
  alias: Process deepstack
  condition: []
  id: '1120092824611'
  trigger:
  - platform: event
    event_type: image_processing.file_saved

"""

file_path = data.get('file_path')
file_name = file_path.split('/')[-1] # get just the file name e.g. img.jpg
web_path = "http://192.168.1.164:8123/local/deepstack_images/" + file_name
logger.info("Deepstack image web_path : {}".format(web_path))

hass.services.call(
    'telegram_bot', 'send_photo', {
        "caption": "{}".format(file_name),
        "url": web_path}
)
