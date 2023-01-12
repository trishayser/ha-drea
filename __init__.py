"""The Drea integration."""
from __future__ import annotations

import traceback

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.typing import ConfigType
from homeassistant.components import mqtt
from homeassistant.util.color import color_rgb_to_rgbw, color_hs_to_RGB
from .const import DOMAIN


# TODO const in const.py
CONF_TOPIC = "topic"
DEFAULT_TOPIC = "drea-test-34321"

ACCECPTABLE_ROTATION_RANGE = 5.0

# TODO List the platforms that you want to support.
# For your initial PR, limit it to 1 platform.
# PLATFORMS: list[Platform] = [Platform.LIGHT]


def convert_drea_data(data_string: str):
    timestamp_str, finger_count_str, rotation_str, rotation_sum_str = data_string.split(",", 3)
    rotation = None
    rotation_sum = None

    timestamp = int(timestamp_str)
    finger_count = int(finger_count_str)
    try:
        rotation = float(rotation_str)
        rotation_sum = float(rotation_sum_str)
    except:
        rotation = None
        rotation_sum = None

    output = {
        "timestamp": timestamp,
        "finger_count": finger_count,
        "rotation": rotation,
        "rotation_sum": rotation_sum,
    }
    return output

def rotation_to_percentage(rotation):
    return (rotation / 270.0) * -1


# TODO check time and radient
def is_tap_gesture(first_message_with_finger, current_message):
    time_first_message = first_message_with_finger["timestamp"]
    time_current_message = current_message["timestamp"]

    rotation_sum_first_message = first_message_with_finger["rotation_sum"]
    rotation_sum_current_message = current_message["rotation_sum"]

    time_check = False
    rotation_check = False
    result = False

    time_range = time_current_message - time_first_message
    rotation_range = abs(rotation_sum_first_message - rotation_sum_current_message)
    if 800 > time_range > 200:
        time_check = True
    if rotation_range < ACCECPTABLE_ROTATION_RANGE:
        rotation_check = True

    return time_check and rotation_check


def get_finger_count_from_dict(finger_count_count_dict):
    return max(finger_count_count_dict, key=finger_count_count_dict.get)


def toggle_entity(hass, entity_id, last_state):
    domain, entity_name = entity_id.split(".", 1)

    if domain == "light":
        if last_state == "off":
            hass.services.call(domain, "turn_on", {"entity_id": entity_id})
        if last_state == "on":
            hass.services.call(domain, "turn_off", {"entity_id": entity_id})
    elif domain == "media_player":
        hass.services.call(domain, "media_play_pause", {"entity_id": entity_id})
    elif domain == "climate":
        if last_state == "off":
            hass.services.call(domain, "turn_on", {"entity_id": entity_id})
        else:
            hass.services.call(domain, "turn_off", {"entity_id": entity_id})


def get_hs_sat_output(rotation, entity_id, entity_state):
    rot_percentage = rotation_to_percentage(rotation)
    if entity_state.state != "off":
        current_hue_color = entity_state.as_dict().get("attributes").get("hs_color")[0] or 0.0
        current_hue_sat = entity_state.as_dict().get("attributes").get("hs_color")[1] or 100.0
        if entity_state is not None:
            hue_sat_step = rot_percentage * 100
            hue_sat_result = current_hue_sat + hue_sat_step
            if hue_sat_result > 100.0:
                hue_sat_result = 100.0
            elif hue_sat_result < 0.0:
                hue_sat_result = 0.0
            output_data = {"entity_id": entity_id, "hs_color": [current_hue_color, hue_sat_result]}
        else:
            output_data = {"entity_id": entity_id}
    else:
        output_data = {"entity_id": entity_id}
    return output_data


def get_rgbw_color_output(rotation, entity_id, entity_state):
    rot_percentage = rotation_to_percentage(rotation)
    if entity_state.state != "off":
        current_hue_color = entity_state.as_dict().get("attributes").get("hs_color")[0]
        if entity_state is not None:
            hue_color_step = rot_percentage * 360
            hue_color_result = current_hue_color + hue_color_step
            if hue_color_result > 360.0:
                hue_color_result = hue_color_result - 360.0
            elif hue_color_result < 0.0:
                hue_color_result = hue_color_result + 360.0
            r, g, b = color_hs_to_RGB(hue_color_result, 100.0)
            r, g, b, w = color_rgb_to_rgbw(int(r), int(g), int(b))
            output_data = {"entity_id": entity_id, "rgbw_color": [r, g, b, w]}
        else:
            output_data = {"entity_id": entity_id}
    else:
        output_data = {"entity_id": entity_id}
    return output_data


def get_brightness_output(rotation, entity_id, entity_state):
    rot_percentage = rotation_to_percentage(rotation)
    if entity_state.state != "off":
        current_brightness = entity_state.as_dict().get("attributes").get("brightness")
    else:
        current_brightness = 0
    brightness_step = rot_percentage * 255
    brightness_result = brightness_step + current_brightness
    if brightness_result > 255.0:
        brightness_result = 255
    elif brightness_result < 0:
        brightness_result = 0
    output_data = {"entity_id": entity_id, "brightness": int(brightness_result)}
    return output_data


def get_climate_temperature_output(rotation, entity_id, entity_state):
    rot_percentage = rotation_to_percentage(rotation)
    current_temperature = entity_state.as_dict().get("attributes").get("temperature")
    min_temp = entity_state.as_dict().get("attributes").get("min_temp")
    max_temp = entity_state.as_dict().get("attributes").get("max_temp")
    temp_range = max_temp - min_temp
    temperature_step = temp_range * rot_percentage
    temperature = current_temperature + temperature_step
    if temperature > max_temp:
        temperature = max_temp
    elif temperature < min_temp:
        temperature = min_temp
    output_data = {"entity_id": entity_id, "temperature": temperature}
    return output_data


def get_media_player_volume_output(rotation, entity_id, entity_state):
    rot_percentage = rotation_to_percentage(rotation)
    current_volume_level = entity_state.as_dict().get("attributes").get("volume_level")
    volume_level_step = rot_percentage * 1
    volume_level_result = current_volume_level + volume_level_step
    if volume_level_result > 1.0:
        volume_level_result = 1.0
    elif volume_level_result < 0.0:
        volume_level_result = 0.0
    output_data = {"entity_id": entity_id, "volume_level": volume_level_result}
    return output_data

def get_rotation_service_data(rotation_init_entity_id, rotation_init_entity_state, attribute, rotation):
    domain, entity_name = rotation_init_entity_id.split(".", 1)
    service = None
    output_data = None

    if domain == "light":
        service = "turn_on"
        if attribute == "brightness":
            output_data = get_brightness_output(rotation, rotation_init_entity_id, rotation_init_entity_state)
        elif attribute == "color_temp":
            output_data = get_color_temp_output(rotation, rotation_init_entity_id, rotation_init_entity_state)
        elif attribute == "color":
            output_data = get_hs_color_output(rotation, rotation_init_entity_id, rotation_init_entity_state)
        elif attribute == "saturation":
            output_data = get_hs_sat_output(rotation, rotation_init_entity_id, rotation_init_entity_state)
        elif attribute == "rgbw_color":
            output_data = get_rgbw_color_output(rotation, rotation_init_entity_id, rotation_init_entity_state)
    elif domain == "media_player":
        if attribute == "volume_level":
            service = "volume_set"
            output_data = get_media_player_volume_output(rotation, rotation_init_entity_id, rotation_init_entity_state)

    elif domain == "climate":
        if attribute == "temperature":
            service = "set_temperature"
            output_data = get_climate_temperature_output(rotation, rotation_init_entity_id, rotation_init_entity_state)


    return domain, service, output_data


def get_hs_color_output(rotation, rotation_init_entity_id, rotation_init_entity_state):
    rot_percentage = rotation_to_percentage(rotation)
    if rotation_init_entity_state.state != "off":
        current_hue_color = rotation_init_entity_state.as_dict().get("attributes").get("hs_color")[0]
        if rotation_init_entity_state is not None:
            hue_color_step = rot_percentage * 360
            hue_color_result = current_hue_color + hue_color_step
            if hue_color_result > 360.0:
                hue_color_result = hue_color_result - 360.0
            elif hue_color_result < 0.0:
                hue_color_result = hue_color_result + 360.0
            output_data = {"entity_id": rotation_init_entity_id, "hs_color": [hue_color_result, 100.0]}
        else:
            output_data = {"entity_id": rotation_init_entity_id}
    else:
        output_data = {"entity_id": rotation_init_entity_id}
    return output_data


def get_color_temp_output(rotation, entity_id, entity_state):
    rot_percentage = rotation_to_percentage(rotation)
    current_color_temp = entity_state.as_dict().get("attributes").get("color_temp") or None
    color_temp_min = entity_state.as_dict().get("attributes").get("min_mireds")
    color_temp_max = entity_state.as_dict().get("attributes").get("max_mireds")
    color_temp_range = color_temp_max - color_temp_min
    if current_color_temp is not None:
        color_temp_step = rot_percentage * color_temp_range
        color_temp_result = int(current_color_temp + color_temp_step)
        if color_temp_result > color_temp_max:
            color_temp_result = color_temp_max
        elif color_temp_result < color_temp_min:
            color_temp_result = color_temp_min
    else:
        color_temp_result = color_temp_max
    output_data = {"entity_id": entity_id, "color_temp": color_temp_result}
    return output_data


def get_entity_attribute_by_finger_count(hass, finger_count):
    entity_dict = get_entity_settings(hass)
    attr_dict = get_attributes_settings(hass)
    entity = entity_dict[finger_count]
    attribute = attr_dict[finger_count]

    return entity, attribute


def get_entity_settings(hass):
    five_finger_entity = hass.config_entries.async_entries("drea")[0].options["five_finger_opt"]
    four_finger_entity = hass.config_entries.async_entries("drea")[0].options["four_finger_opt"]
    three_finger_entity = hass.config_entries.async_entries("drea")[0].options["three_finger_opt"]
    two_finger_entity = hass.config_entries.async_entries("drea")[0].options["two_finger_opt"]
    entity_dict = {
        2: two_finger_entity,
        3: three_finger_entity,
        4: four_finger_entity,
        5: five_finger_entity
    }
    return entity_dict


def get_attributes_settings(hass):
    five_finger_attr = hass.config_entries.async_entries("drea")[0].options["five_finger_attr"] or None
    four_finger_attr = hass.config_entries.async_entries("drea")[0].options["four_finger_attr"] or None
    three_finger_attr = hass.config_entries.async_entries("drea")[0].options["three_finger_attr"] or None
    two_finger_attr = hass.config_entries.async_entries("drea")[0].options["two_finger_attr"] or None
    attr_dict = {
        2: two_finger_attr,
        3: three_finger_attr,
        4: four_finger_attr,
        5: five_finger_attr
    }
    return attr_dict


def setup(hass: HomeAssistant, config: ConfigType) -> bool:
    topic = "drea"
    entity_id = "drea.last_message"

    def message_received(topic: str, payload: str, qos: int) -> None:
        """A new MQTT message has been received."""
        current_message = convert_drea_data(payload)
        toggle_activated = False
        finger_count_count_dict = {}
        first_message_with_finger = {}
        rotation_init_attr = None
        rotation_state_dict = None
        last_state = None
        tap_finger_count = None
        output_state_attr = {}




        try:
            current_state = hass.states.get(entity_id).as_dict()

            # init values from state
            last_message = convert_drea_data(current_state.get("attributes").get("last_message"))
            finger_count_count_dict = current_state.get("attributes").get("finger_count_count")
            first_message_with_finger = current_state.get("attributes").get("first_message_with_finger")
            rotation_state_dict = current_state.get("attributes").get("rotation_state_dict")

            if current_message["finger_count"] == 0 and last_message["finger_count"] >= 1:
                if is_tap_gesture(first_message_with_finger, current_message) is True:
                    toggle_activated = True
                    tap_finger_count = get_finger_count_from_dict(finger_count_count_dict)
                    last_state = rotation_state_dict[tap_finger_count].state
                else:
                    finger_count_count_dict = {}
                    first_message_with_finger = {}
                    rotation_state_dict = None

            elif last_message["finger_count"] == 0 and current_message["finger_count"] >= 1:
                first_message_with_finger = current_message
                entity_settings_dict = get_entity_settings(hass)
                rotation_state_dict = {
                    2: hass.states.get(entity_settings_dict[2]),
                    3: hass.states.get(entity_settings_dict[3]),
                    4: hass.states.get(entity_settings_dict[4]),
                    5: hass.states.get(entity_settings_dict[5])
                }
                finger_count_count_dict = {
                    2: 0,
                    3: 0,
                    4: 0,
                    5: 0
                }
                if current_message["finger_count"] >= 2:
                    finger_count_count_dict[current_message["finger_count"]] += 1
            elif current_message["finger_count"] >= 2:
                finger_count_count_dict[current_message["finger_count"]] += 1
                print(str(finger_count_count_dict))
                if current_message["rotation_sum"] is not None and first_message_with_finger["rotation_sum"] is not None:
                    rotation = current_message["rotation_sum"] - first_message_with_finger["rotation_sum"]
                    rot_entity_id, rot_attribute = get_entity_attribute_by_finger_count(hass, get_finger_count_from_dict(finger_count_count_dict))
                    domain, service, output_data = get_rotation_service_data(rot_entity_id, rotation_state_dict[get_finger_count_from_dict(finger_count_count_dict)], rot_attribute, rotation)
                    hass.services.call(domain, service, output_data)

            elif current_message["finger_count"] == 0 and last_message["finger_count"] == 0:
                finger_count_count_dict = {}
                first_message_with_finger = {}
                rotation_state_dict = {}

            output_state_attr["finger_count_count"] = finger_count_count_dict
            output_state_attr["first_message_with_finger"] = first_message_with_finger
            output_state_attr["rotation_state_dict"] = rotation_state_dict

        except Exception:
            print("RESET")
            print(str(current_message))
            print(traceback.format_exc())
            #output_state_attr["finger_count_count"] = {}
            output_state_attr["first_message_with_finger"] = {}
            output_state_attr["rotation_state_dict"] = {}

        if toggle_activated is True and tap_finger_count is not None:
            toggle_entity(hass, get_entity_settings(hass)[tap_finger_count], last_state)

        output_state_attr["last_message"] = payload
        hass.states.set(entity_id, str(payload), output_state_attr)

    hass.components.mqtt.subscribe(topic, message_received)
    hass.states.set(entity_id, "No messages")

    def set_state_service(call: ServiceCall) -> None:
        """Service to send a message."""
        hass.components.mqtt.publish(topic, call.data.get("new_state"))

    # Register our service with Home Assistant.
    hass.services.register(DOMAIN, "set_state", set_state_service)
    return True



async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    return True


