#!/usr/bin/python
"""Script to implement a multi channel pulse counter that
posts to the mini-monitor MQTT broker.

This script should be started by a supervisor capable of restarting
the script if an error occurs.
"""
import time
import sys
import argparse
import input_change
import mqtt_poster

# GPIO Pins (BCM numbering) used by the pulse counter
PIN_IN_DEFAULTS = [16, 17]     # the pulse input pins to use if no values in settings file
PIN_DEBUG = 5   # an output pin used for debugging

# Count at which counter rolls to zero
ROLLOVER = 1000000

# process command line arguments
parser = argparse.ArgumentParser(description='Single Channel Pulse Counter Script.')
parser.add_argument("-d", "--debug", help="turn on Debug pin", action="store_true")
args = parser.parse_args()

# set the debug pin if requested
debug_pin = PIN_DEBUG if args.debug else None

# Access some settings in the Mini-Monitor settings file
# The settings file is installed in the FAT boot partition of the Pi SD card,
# so that it can be easily configured from the PC that creates the SD card.  
# Include that directory in the Path so the settings file can be found.
sys.path.insert(0, '/boot/pi_logger')
import settings

# get list of input pins
pin_in_list =  getattr(settings, 'PULSE_INPUT_PINS', PIN_IN_DEFAULTS)

# get logging interval in seconds
log_interval = getattr(settings, 'PULSE_LOG_INTERVAL', 10 * 60)

# flag to determine if both transitions are counted
count_both = getattr(settings, 'PULSE_BOTH_EDGES', False)

# start up the object that posts to the MQTT broker
poster = mqtt_poster.MQTTposter()
poster.start()

# Track pulse counts in a dictionary indexed on pin number
pulse_count = dict(zip(pin_in_list, [0] * len(pin_in_list)))

def chg_detected(pin_num, new_state):
    """This is called when the pulse input pin changes state.
    """
    global pulse_count

    if new_state == False or count_both:
        pulse_count[pin_num] += 1
        pulse_count[pin_num] = pulse_count[pin_num] % ROLLOVER

# Start up the Input Pin Change Detector
# I have a 10 K pull-up on the board and a 0.01 uF cap to ground.
chg_detect = input_change.InputChange(pin_in_list, chg_detected, pull_up=False, debug_pin=debug_pin)
chg_detect.start()

# determine time to log count
next_log_ts = time.time() + log_interval

while True:

    if not chg_detect.isAlive() or not poster.isAlive():
        # an important thread is not running.  Exit with an error.
        sys.exit(1)

    ts = time.time()
    if ts > next_log_ts:
        lines = []
        for pin_num, ct in pulse_count.items():
            lines.append('%s\t%s\t%s' % (int(ts), '%s_%2d_pulse' % (settings.LOGGER_ID, pin_num), ct))
        poster.publish('readings/final/pulse_counter_multi', '\n'.join(lines))
        if args.debug:
            print pulse_count
        next_log_ts += log_interval

    time.sleep(0.2)
