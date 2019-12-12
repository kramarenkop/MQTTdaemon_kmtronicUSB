__author__ = "Miguel Rivas"
__copyright__ = "2019 Miguel Rivas"
__credits__ = ["Miguel Rivas"]
__license__ = "GPL-3.0"
__version__ = "1.0.2"

# MQTTdaemon for KMTronic USB-serial relay boards
# https://github.com/migrivas/MQTTdaemon_kmtronicUSB

import serial
import time
import random
import json
import uuid
import sys
import logging
from config import *
from datetime import datetime
from daemonizer import daemon
import paho.mqtt.client as mqtt

# Logging
logging.basicConfig(
    filename=logfile,
	filemode='a',
    maxBytes=5242880,
    backupCount=2,
	format='[%(asctime)s] %(message)s',
	datefmt='%Y-%d-%m %H:%M:%S',
	level=logging.INFO)

# Array that stores the relays' statuses
relaystates={}              # will be auto set per each device later
state_topic=""              # will be auto set per each device later
lwt_online="Online"         # Online message
lwt_offline="Offline"       # Offline message
cmd_on="ON"                 # "On" command
cmd_off="OFF"               # "Off" command
cmd_toggle="TOGGLE"         # "Toggle" command
client = None

# Gets an ID from MAC address to idenfity the client on MQTT server
def get_uuid():
	mac_num = hex(uuid.getnode()).replace('0x', '').replace('L', '')
	mac_num = mac_num.zfill(12)
	mac = ''.join(mac_num[i : i + 2] for i in range(0, 11, 2))
	return mac[6:]

# We connect to the serial port on-demand.
def serialconnect(device):
    ser=serial.Serial()
    logging.info("[Board="+device['mqtt_topic']+"] INFO Opening connection to serial port " + device['serial_port'])
    try:
        ser=serial.Serial(
            port=device['serial_port'],\
            baudrate=9600,\
            bytesize=serial.EIGHTBITS,\
            parity=serial.PARITY_NONE,\
            stopbits=serial.STOPBITS_ONE,\
            timeout=0,\
            xonxoff=True)
        logging.info("[Board="+device['mqtt_topic']+"] INFO Connected to: " + ser.portstr)
    except:
        logging.info("[Board="+device['mqtt_topic']+"] INFO Unable to open serial port. Check if the board is plugged-in and permissions.")
    return ser
# We set the relays with its current status returned from the board.
def relayinit(device):
    ser=serialconnect(device)
    this_device = device['mqtt_topic']
    relaystates[this_device]=[False, False, False, False, False, False, False, False]
    tmpstatus = [0,0,0,0,0,0,0,0]
    logging.info("[Board="+device['mqtt_topic']+"] INFO Requesting status of "+str(device['relays_count'])+" relays on USB board " + ser.portstr)
    ser.write(serial.to_bytes([0xFF,0x09,0x00]))
    logging.info("[Board="+device['mqtt_topic']+"] INFO Reading current status from " + ser.portstr)
    time.sleep(1)
    #ser.timeout = 2
    ser.setDTR(1)
    count = 0
    tmplog = ""
    timeout = time.time() + 30   # 30 seconds from now
    while True:
        tmp = ser.read(1)
        if tmp.__len__() == 0:
            break
        if count == device['relays_count']+1:
            break
        if time.time() > timeout:
            logging.info("[Board="+device['mqtt_topic']+"] WARNING Timeout: exiting after 30 seconds reading from "+ ser.portstr)
            break
        tmp = str(hex(ord(tmp))[2:])
        tmplog = tmplog + " " + str(count) + "=>" + tmp
        if tmp == "1":
            relaystates[this_device][count] = True
            tmpstatus[count] = 1
        elif tmp == "0":
            relaystates[this_device][count] = False
            tmpstatus[count] = 0
        time.sleep(0.05)
        count = count + 1
    # Setting the relay states
    if tmplog == "":
        logging.info("[Board="+device['mqtt_topic']+"] WARNING could not read from "+ ser.portstr+", retrying")
        relayinit(device)
    logging.info("[Board="+device['mqtt_topic']+"] INFO "+ ser.portstr + " returned:"+tmplog)
    logging.info("[Board="+device['mqtt_topic']+"] INFO Updating initial status of "+str(device['relays_count'])+" relays on MQTT server")
    state_topic="stat/"+device['mqtt_topic']+"/POWER" # State topic name
    for i in range(0, device['relays_count']+1):
        statetopic=state_topic+("" if i==0 else str(i))
        if i==0:
            i=1
            to_set=tmpstatus[0]
        else:
            to_set=tmpstatus[i-1]
        if to_set == 1:
            this_payload = cmd_on
        else:
            this_payload = cmd_off
        mqtt_publish(client, statetopic, this_payload, True, device)
        time.sleep(0.15)
    logging.info("[Board="+device['mqtt_topic']+"] INFO MQTT status updated for relay " + ser.portstr)
# Relay on
def on(relay, device):
    logging.info("[Board="+device['mqtt_topic']+"] INFO Setting relay to "+str(relay)+" ON")
    ser=serialconnect(device)
    ser.write(serial.to_bytes([0xFF,relay,0x01]))
    time.sleep(0.05)
    this_device = device['mqtt_topic']
    relaystates[this_device][relay-1]=True
# Relay off
def off(relay, device):
    logging.info("[Board="+device['mqtt_topic']+"] INFO Setting relay to "+str(relay)+" OFF")
    ser=serialconnect(device)
    ser.write(serial.to_bytes([0xFF,relay,0x00]))
    time.sleep(0.05)
    this_device = device['mqtt_topic']
    relaystates[this_device][relay-1]=False
# Relay toggle
def toggle(relay, device):
    logging.info("[Board="+device['mqtt_topic']+"] INFO Setting relay to "+str(relay)+" TOGGLE")
    this_device = device['mqtt_topic']
    relaystates[this_device][relay-1]=not(relaystates[this_device][relay-1])
    ser=serialconnect(device)
    ser.write(serial.to_bytes([0xFF,relay, 0x01 if relaystates[relay-1] else 0x00 ]))
    time.sleep(0.05)
# Returns relay status as string
def state(relay, device):
    this_device = device['mqtt_topic']
    return cmd_on if relaystates[this_device][relay-1] else cmd_off
def mqtt_publish(client, topic, payload, retain, device):
    logging.info("[Board="+device['mqtt_topic']+"] INFO ["+topic+"] "+str(payload)+(" (retained)" if retain else ""))
    client.publish(topic, payload, 1, retain)
# Purges discovery topics
def purge_discovery(client, device):
    for i in range(1, device['relays_count']+1):
        topic=mqtt_discovery_prefix+"/switch/"+device['mqtt_topic']+"_"+str(i)+"/config"
        mqtt_publish(client, topic, "", True, device)
# Sends MQTT discovery messages
def send_discovery(client, device):
    for i in range(1, device['relays_count']+1):
        topic=mqtt_discovery_prefix+"/switch/"+device['mqtt_topic']+"_"+str(i)+"/config"
        lwt_topic="tele/"+device['mqtt_topic']+"/LWT"     # Online/Offline topic name
        cmd_topic="cmnd/"+device['mqtt_topic']+"/POWER"   # Command topic name
        state_topic="stat/"+device['mqtt_topic']+"/POWER" # State topic name
        payload = {
            "name": "KMTronic "+device['mqtt_topic']+" "+str(i),
            "cmd_t": cmd_topic+str(i),
            "stat_t": state_topic+str(i),
            "pl_off": "OFF",
            "pl_on": "ON",
            "avty_t": lwt_topic,
            "pl_avail": "Online",
            "pl_not_avail": "Offline",
            "uniq_id": device['mqtt_topic']+"_"+str(i),
            "device": {
                "identifiers": [
                    device['mqtt_topic']
                ],
                "name": "KMTronic "+str(device['relays_count'])+"-relay USB Relay Box",
                "model": "via MQTTdaemon for KMTronic USB-serial",
                "sw_version": __version__,
                "manufacturer": __author__
            }
        }
        mqtt_publish(client, topic, json.dumps(payload), False, device)

def on_disconnect(client, userdata, rc):
    print("")
    logging.info("[Main process] MQTT - Disconnected")
    for device in devices.values():
        lwt_topic="tele/"+device['mqtt_topic']+"/LWT"     # Online/Offline topic name
        mqtt_publish(client, lwt_topic, lwt_offline, True, device)
    print("")
def on_connect(client, userdata, flags, rc):
    logging.info("[Main process] MQTT - Connected: result code "+str(rc))
    for device in devices.values():
        logging.info("[Board="+device['mqtt_topic']+"] INFO Publishing MQTT online status")
        lwt_topic="tele/"+device['mqtt_topic']+"/LWT"     # Online/Offline topic name
        cmd_topic="cmnd/"+device['mqtt_topic']+"/POWER"   # Command topic name
        state_topic="stat/"+device['mqtt_topic']+"/POWER" # State topic name
        # Initializing relays - updating their current status
        logging.info("[Board="+device['mqtt_topic']+"] INFO Initializing relays and updating their current states")
        relayinit(device)
        # Publising availability
        logging.info("[Board="+device['mqtt_topic']+"] INFO Publishing device availability ["+lwt_topic+"]="+lwt_online)
        mqtt_publish(client, lwt_topic, lwt_online, True, device)
        if mqtt_discovery:
            # Sending MQTT discovery messages if enabled
            send_discovery(client, device)
            # Purging previously retained MQTT discovery messages
            purge_discovery(client, device)
        # Subscribing to the necessary amount of command topics
        for i in range(0, device['relays_count']+1):
            topic=cmd_topic+("" if i==0 else str(i))
            client.subscribe(topic)
            logging.info("[Board="+device['mqtt_topic']+"] INFO Subscribed to "+topic)
        client.will_set(lwt_topic, lwt_offline, 1, True)

def on_message(client, userdata, msg):
    message=msg.payload.decode().upper()
    logging.info("[Main process] New message ["+msg.topic+"] = "+message)
    # Check if this request if for a configured board
    this_topic = msg.topic.split("/",3)
    this_topic = this_topic[1]
    for device in devices.values():
        if (device['mqtt_topic'] == this_topic):
            this_topic = device['mqtt_topic']
            break
    if (device['mqtt_topic'] != this_topic):
        logging.info("[Main process] WARNING "+this_topic+ " is not present in config and I cannot manage it")
        this_topic = ""
    cmd_topic="cmnd/"+this_topic+"/POWER"   # Command topic name
    state_topic="stat/"+this_topic+"/POWER" # State topic name
    for i in range(0, device['relays_count']+1):
        cmdtopic=cmd_topic+("" if i==0 else str(i))
        statetopic=state_topic+("" if i==0 else str(i))
        # Handling POWER equal to POWER1
        if i==0:
            i=1
        if msg.topic==cmdtopic:
            if cmd_on in message:
                on(i, device)
            if cmd_off in message:
                off(i, device)
            if cmd_toggle in message:
                toggle(i, device)
            mqtt_publish(client, statetopic, state(i, device), True, device)

def start_process():
    global client
    logging.info("-----------------------------------------------------------------")
    logging.info("        MQTTdaemon for KMTronic USB relay boards - v"+__version__)
    logging.info("        https://github.com/migrivas/MQTTdaemon_kmtronicUSB")
    logging.info("-----------------------------------------------------------------")
    client = mqtt.Client(client_id="kmtronic-"+get_uuid())
    client.on_connect=on_connect
    client.on_message=on_message
    client.on_disconnect=on_disconnect
    client.username_pw_set(mqtt_username, mqtt_password)
    try:
        logging.info("[Main process] Initializing relays and updating current states")
        client.connect(mqtt_host, mqtt_port, 60)
        client.loop_forever()
    except KeyboardInterrupt:
        client.disconnect()

class MyDaemon(daemon):
    def run(self):
        logging.info('--------------')
        logging.info('Daemon Started')
        start_process()
        while True:
            logging.info(time.strftime("%I:%M:%S %p"))
            time.sleep(2)
        logging.info('Daemon Ended')

    def down(self):
        if client != None:
            client.disconnect()

if __name__ == "__main__":
    daemonx = MyDaemon(pidfile)
    print("-----------------------------------------------------------------")
    print("        MQTTdaemon for KMTronic USB relay boards - v"+__version__)
    print("        https://github.com/migrivas/MQTTdaemon_kmtronicUSB")
    print("-----------------------------------------------------------------")
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemonx.start()
            print ""
        if 'start-nodaemon' == sys.argv[1]:
            consoleDisplay = logging.StreamHandler()
            logFormatter = logging.Formatter("%(asctime)s %(message)s","%Y-%m-%d %H:%M:%S")
            consoleDisplay.setFormatter(logFormatter)
            logging.getLogger().addHandler(consoleDisplay)
            start_process()
        elif 'stop' == sys.argv[1]:
            consoleDisplay = logging.StreamHandler()
            logFormatter = logging.Formatter("%(asctime)s %(message)s","%Y-%m-%d %H:%M:%S")
            consoleDisplay.setFormatter(logFormatter)
            logging.getLogger().addHandler(consoleDisplay)
            daemonx.stop()
            logging.info('Daemon Stopped')
            print ""
        elif 'restart' == sys.argv[1]:
            print("Restarting process...")
            logging.info('Daemon restarting')
            daemonx.restart()
            print ""
        else:
            print("Unknown command")
            print ""
            sys.exit(2)
        sys.exit(0)
    else:
        print("Usage: %s start|stop|restart|start-nodaemon" % sys.argv[0])
        sys.exit(2)
