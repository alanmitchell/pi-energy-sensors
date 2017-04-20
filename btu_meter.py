#!/usr/bin/python
"""Script to implement a BTU meter that uses a pulse output flow meter
and two thermistors to measure hydronic heat flow.  Results are posted
to the mini-monitor MQTT broker.

This script should be started by a supervisor capable of restarting
the script if an error occurs.
"""
import time
import sys
import argparse
import input_change
import mqtt_poster
import RPi.GPIO as GPIO

# GPIO Pins (BCM numbering) and ADC channels used by the BTU METER
PIN_PULSE_IN = 13
PIN_CALIBRATE = 4
PIN_LED = 16
PIN_DEBUG = 5
ADC_CH_THOT = 0
ADC_CH_TCOLD = 1

# Make the LED pin an output
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN_LED, GPIO.OUT)

# Count at which pulse counter rolls to zero
PULSE_ROLLOVER = 1000000

# Value at which the heat count rolls over.  This is a sum of the delta-Ts
# that are present when pulses occur.
HEAT_ROLLOVER = 1000000.0

# process command line arguments
parser = argparse.ArgumentParser(description='BTU Meter Script.')
parser.add_argument("-d", "--debug", help="turn on Debug pin", action="store_true")
parser.add_argument("-b", "--both", help="count both low-to-high and high-to-low transitions", 
        action="store_true")
args = parser.parse_args()

# set the debug pin if requested
debug_pin = PIN_DEBUG if args.debug else None

# flag to determine if both transitions are counted
count_both = args.both

# Access some settings in the Mini-Monitor settings file
# The settings file is installed in the FAT boot partition of the Pi SD card,
# so that it can be easily configured from the PC that creates the SD card.  
# Include that directory in the Path so the settings file can be found.
sys.path.insert(0, '/boot/pi_logger')
import settings

# make a sensor id
sensor_id = '%s_%2d_btu' % (settings.LOGGER_ID, PIN_PULSE_IN)

# get logging interval in seconds
log_interval = settings.LOG_INTERVAL

# start up the object that posts to the MQTT broker
poster = mqtt_poster.MQTTposter()
poster.start()

pulse_count = 0

def chg_detected(pin_num, new_state):
    """This is called when the input pin changes state.
    """
    global pulse_count

    if pin_num == PIN_PULSE_IN:
        if new_state:
            # always count low-to-high transition
            pulse_count += 1
        elif count_both:
            # only count high-to-low if requested
            pulse_count += 1
        pulse_count = pulse_count % PULSE_ROLLOVER

    elif pin_num == PIN_CALIBRATE:
        if new_state == False:
            time.sleep(1.0)
            if GPIO.input(PIN_CALIBRATE)==False:
                GPIO.output(PIN_LED, True)
                time.sleep(1.0)
                GPIO.output(PIN_LED, False)
                # perform calibration here

# Start up the Input Pin Change Detector
# I have a 10 K pull-up on the board and a 0.01 uF cap to ground.
chg_detect = input_change.InputChange([PIN_PULSE_IN, PIN_CALIBRATE], chg_detected, pull_up=False, debug_pin=debug_pin)
chg_detect.start()

# determine time to log count
next_log_ts = time.time() + log_interval

while True:

    if not chg_detect.isAlive():
        # change detector is not running.  Exit with an error
        sys.exit(1)

    ts = time.time()
    if ts > next_log_ts:
        poster.publish('readings/final/btu_meter', '%s\t%s\t%s' % (int(ts), sensor_id, pulse_count))
        next_log_ts += log_interval

    time.sleep(0.5)
