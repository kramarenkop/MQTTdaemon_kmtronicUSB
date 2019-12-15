# MQTTdaemon for KMTronic USB relay boards
This Python daemon creates a link between a MQTT server and KMtronic USB/serial RS232 relay boards.
So you can easily control these relays remotely and integrate them in [HomeAssistant](https://www.home-assistant.io/) or any other home automation system.

## Some features
- It reads current relay states on init and updates the MQTT server accordingly. So if the MQTT server didn't keep a previous state, the relays will be set to their current actual state. If the MQTT had retained states, they will be updated after reading.
- It controls one or multiple USB relay-boards listening MQTT commands
- Execution available in daemon or normal mode
  `python mqttdaemon.py start` or `python mqttdaemon.py start-nodaemon`
- **HomeAssistant MQTT Discovery** - The daemon can automatically add the relays as switches in HomeAssistant if you set the option `mqtt_discovery` to `True` in `config.py` file. Keep this setting to `False` if you prefer to create HomeAssistant entities manually.

## MQTT commands
| MQTT command | Description |
| ------------- | ------------- |
| `cmd/{BOARDTOPIC}/POWER{relay}`  | turn (ON/OFF/TOGGLE)  |
| `stat/{BOARDTOPIC}/POWER{relay}`  | returns the state of the relay (ON/OFF)  |
| `tele/{BOARDTOPIC}/LWT`  | returns the state of the board (Online/Offline)  |

## Installation
1. Download and unzip or clone project
2. Install requirements
   `python -m pip install -r requirements.txt`
3. Rename or copy `config.install.py` to `config.py`
4. Edit `config.py` to configure
5. Execute the daemon
   `python mqttdaemon.py start`

## Configuration
The [configuration file](https://github.com/migrivas/MQTTdaemon_kmtronicUSB/blob/master/config.install.py) is pretty straightforward.
Rename it to config.py, and edit it as needed.

## Daemon options
| Command | Description |
| ------------- | ------------- |
| `python mqttdaemon.py start`  | Start daemon  |
| `python mqttdaemon.py start-nodaemon`  | Run in the same console, without daemon  |
| `python mqttdaemon.py restart`  | Restart  |
| `python mqttdaemon.py stop`  | Stop  |

## Configuration for HomeAssistant
If you want to use [HomeAssistant](https://www.home-assistant.io/), you have two options:
- Configure the switches manually setting `mqtt_discovery` to `False` on `config.py`.
  Use the example below as reference to configure HomeAssistant:
```
# Example HomeAssistant configuration.yaml entry
switch:
  - platform: mqtt
    name: kmtronic_board1_relay5
    state_topic: "stat/kmtronic1/POWER5"
    command_topic: "cmnd/kmtronic1/POWER5"
    availability_topic: "tele/kmtronic1/LWT"
    qos: 1
    payload_on: "ON"
    payload_off: "OFF"
    payload_available: "Online"
    payload_not_available: "Offline"
    retain: true
  - platform: mqtt
    name: kmtronic_board1_relay6
    state_topic: "stat/kmtronic1/POWER6"
    command_topic: "cmnd/kmtronic1/POWER6"
    availability_topic: "tele/kmtronic1/LWT"
    qos: 1
    payload_on: "ON"
    payload_off: "OFF"
    payload_available: "Online"
    payload_not_available: "Offline"
    retain: true
# And so on...

mqtt:
  broker: 127.0.0.1
  port: 1883
  client_id: home-assistant-1
  username: Your_username
  password: Your_password
```    
- Or use the auto-discovery to let homeassistant configure the relays setting `mqtt_discovery` to `True` on `config.py`
```
# Example HomeAssistant configuration.yaml entry
mqtt:
  broker: 127.0.0.1
  port: 1883
  client_id: home-assistant-1
  username: Your_username
  password: Your_password
  discovery: true
  discovery_prefix: homeassistant
```

## Test the relays
Once the daemon is loaded, you can check its log file:
`tail -f /var/log/mqttdaemon.log`

You can use any MQTT client. With the Mosquitto client ([mosquitto_pub](https://manpages.debian.org/testing/mosquitto-clients/mosquitto_pub.1.en.html)) you can test turning a relay on, using the command line:
`mosquitto_pub -h 127.0.0.1 -u {Your_username} -P {Your_password} -t cmnd/{your_board_mqtt_topic}/POWER6 -m "ON"`

## Requirements
- Python3
- A MQTT server installed (ie. [Mosquitto](https://mosquitto.org/))
- One (or multiple) KMtronic USB/Serial board connected to the machine running the daemon.

## Note
Tested with:
- OS: **Linux** Debian/Ubuntu
- Hardware: [KMTronic 8-Channel USB relay boards](https://sigma-shop.com/product/8/-usb-eight-channel-relay-controller-serial-controlled-12v-ftdi-.html) (with /dev/ttyUSB* and /dev/ttyACM* ports)

## Credits
- This project is based on an original work from [donatmarko](https://github.com/donatmarko/kmtronic-usb-relaybox-mqtt). I've added some additional features (daemon mode, support for multiple boards, reading states on init, logging...).
- Libraries: [Paho MQTT](https://pypi.org/project/paho-mqtt/) and [Pyserial](https://github.com/pyserial/pyserial)
