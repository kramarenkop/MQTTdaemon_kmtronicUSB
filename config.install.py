# CONFIGURATION FILE - rename to config.py   !!!!
#                      -------------------
# Enables MQTT discovery for Home-Assistant to detect the relays automatically
mqtt_discovery=False
# Prefix for Home-Assistant MQTT discovery (default = "homeassistant")
mqtt_discovery_prefix="homeassistant"
# MQTT connection data
mqtt_host="127.0.0.1"
mqtt_port=1883
mqtt_username="Your-user"
mqtt_password="Your-password"
logfile="/var/log/mqttdaemon.log"
pidfile='/tmp/mqttdaemon.pid'
# You can add multiple Kmtronic USB relay boards to this array
# Define a [unique_key_number]: { "serial_port": "[your_serial_port]", "relays_count": [number_of_relays], "mqtt_topic": "[unique_name]"}
devices = {
    0: {
        # serial_port -Serial port for realy board
        "serial_port": "/dev/ttyACM0",
        # relays_count - Number of relays in the board
        "relays_count": 8,
        # mqtt_topic - MQTT topic domain, usually a friendly name for the device
        # IMPORTANT: set an UNIQUE name per board, single word with no special chars
        # Don't use full (e.g. cmnd/kmtronic/POWER) addresses!
        "mqtt_topic":"kmtronic2"
    }
    # You can add multiple devices:, just remove # if needed:
    #, 1: { "serial_port": "/dev/ttyUSB0", "relays_count": 8, "mqtt_topic":"kmtronic1" }
    #, 2: { "serial_port": "/dev/ttyUSB1", "relays_count": 8, "mqtt_topic":"kmtronic2" }
}
