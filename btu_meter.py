#!/usr/bin/python
"""Script to implement a BTU meter that uses a pulse output flow meter
and two thermistors to measure hydronic heat flow.  Results are posted
to the mini-monitor MQTT broker.

This script should be started by a supervisor capable of restarting
the script if an error occurs.

This script must be run with sudo because it writes to the /var/local 
directory.
"""
import time
import sys
import os
import argparse
import shutil
import RPi.GPIO as GPIO
import input_change
import mqtt_poster
import thermistor

# Import SPI library (for hardware SPI) and MCP3008 library.
import Adafruit_GPIO.SPI as SPI
import Adafruit_MCP3008

# GPIO Pins (BCM numbering) and ADC channels used by the BTU METER
PIN_PULSE_IN = 13
PIN_CALIBRATE = 4
PIN_LED = 16
PIN_DEBUG = 5
ADC_CH_THOT = 0
ADC_CH_TCOLD = 1

# Eliminate GPIO warnings
GPIO.setwarnings(False)

# Make the LED pin an output
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN_LED, GPIO.OUT)

# Count at which pulse counter rolls to zero
PULSE_ROLLOVER = 1000000

# Value at which the heat count rolls over.  This is a sum of the delta-Ts
# that are present when pulses occur.
HEAT_ROLLOVER = 1000000.0

# Number of A/D readings to average together to get the 
# current temperature reading.
BUF_LEN_TEMP = 100

# Path to temperature calibration file
PATH_CALIBRATE = '/var/local/btu_calibration'

# process command line arguments
parser = argparse.ArgumentParser(description='BTU Meter Script.')
parser.add_argument("-d", "--debug", help="Set Debug mode", action="store_true")
args = parser.parse_args()

# set the debug pin if requested
debug_pin = PIN_DEBUG if args.debug else None

# Access some settings in the Mini-Monitor settings file
# The settings file is installed in the FAT boot partition of the Pi SD card,
# so that it can be easily configured from the PC that creates the SD card.  
# Include that directory in the Path so the settings file can be found.
sys.path.insert(0, '/boot/pi_logger')
import settings

# make a base sensor id
base_sensor_id = '%s_%2d_btu' % (settings.LOGGER_ID, PIN_PULSE_IN)

# get logging interval in seconds
log_interval = getattr(settings, 'BTU_LOG_INTERVAL', 10 * 60)

# get the minimum delta-T required to tally energy flow (deg F)
min_delta_T = getattr(settings, 'BTU_MIN_DELTA_T', 0.2)

# flag to determine if both transitions are counted
count_both = getattr(settings, 'BTU_BOTH_EDGES', False)

# start up the object that posts to the MQTT broker
poster = mqtt_poster.MQTTposter()
poster.start()

# make a thermistor object to convert A/D readings into temperature.
# Using a 4.99 K divider resistor and a 10-bit A/D converter with max
# value of 1023.
therm = thermistor.Thermistor('BAPI 10K-3', appliedV=1023.0, dividerR=4990.0)

# Initialize pulse count and heat count
pulse_count = 0
heat_count = 0.0

# Set up MCP3008 A/D converter.  We are using the hardware SPI port
# on the Raspberry Pi (to save CPU cycles).
SPI_PORT   = 0
SPI_DEVICE = 0
mcp = Adafruit_MCP3008.MCP3008(spi=SPI.SpiDev(SPI_PORT, SPI_DEVICE))

# Initialize arrays to hold hot and cold thermistor A/D readings.
# These arrays are used to calculate a current reading that is
# an average of recent readings.  The raw A/D counts are stored
# in the array to elimnate the CPU time needed to convert each into
# a temperature.  Variation between the readings is small, so the
# non-linearity of the count-->temperature function is not important.
ad_hot = [mcp.read_adc(ADC_CH_THOT)] * BUF_LEN_TEMP
ad_cold = [mcp.read_adc(ADC_CH_TCOLD)] * BUF_LEN_TEMP

# read in the temperature calibration coefficients if the file exists
if os.path.exists(PATH_CALIBRATE):
    with open(PATH_CALIBRATE, 'r') as fin:
        calibrate_hot = float(fin.readline())
        calibrate_cold = float(fin.readline())
else:
    calibrate_hot = 0.0
    calibrate_cold = 0.0

def current_temps(include_calibration=True):
    """Returns the current hot and cold temperatures, averaging the values
    in the reading buffer.  If 'include_calibration' is True, apply the
    calibration values.
    """
    thot = sum(ad_hot)/float(BUF_LEN_TEMP)
    thot = therm.TfromV(thot)
    if include_calibration:
        thot += calibrate_hot
    tcold = sum(ad_cold)/float(BUF_LEN_TEMP)
    tcold = therm.TfromV(tcold)
    if include_calibration:
        tcold += calibrate_cold
    return thot, tcold

def chg_detected(pin_num, new_state):
    """This is called when the input pin changes state.
    """
    global pulse_count, heat_count
    global calibrate_hot, calibrate_cold

    if pin_num == PIN_PULSE_IN:
        # get current temperatures
        thot, tcold = current_temps()
        delta_T = thot - tcold
        # enforce minimum delta-T
        if abs(delta_T) < min_delta_T:
            delta_T = 0.0
        if new_state:
            # always count low-to-high transition
            pulse_count += 1
            heat_count += delta_T
        elif count_both:
            # only count high-to-low if requested
            pulse_count += 1
            heat_count += delta_T
        pulse_count = pulse_count % PULSE_ROLLOVER
        heat_count = heat_count % HEAT_ROLLOVER

    elif pin_num == PIN_CALIBRATE:
        if new_state == False:
            # Calibrate button was pressed
            # Check a second later to see if it is still pressed.
            # Note that this interrupts pulse counting.
            time.sleep(1.0)
            if GPIO.input(PIN_CALIBRATE)==False:
                # blink LED to indicate that calibrate function will occur
                GPIO.output(PIN_LED, True)
                time.sleep(1.0)
                GPIO.output(PIN_LED, False)

                # calibrate process
                thot, tcold = current_temps(include_calibration=False)
                true_temp = (thot + tcold)/2.0  # deemed the true temp
                calibrate_hot = true_temp - thot
                calibrate_cold = true_temp - tcold
                # backup old calibration values and store new values
                shutil.copy(PATH_CALIBRATE, PATH_CALIBRATE + '.bak')
                with open(PATH_CALIBRATE, 'w') as fout:
                    fout.write('%s\n' % calibrate_hot)
                    fout.write('%s\n' % calibrate_cold)

# Start up the Input Pin Change Detector
# I have a 10 K pull-up on the board and a 0.01 uF cap to ground.
chg_detect = input_change.InputChange([PIN_PULSE_IN, PIN_CALIBRATE], chg_detected, pull_up=False, debug_pin=debug_pin)
chg_detect.start()

# determine time to log count
next_log_ts = time.time() + log_interval

# index into temperature reading buffer arrays
ix = 0

while True:

    if not chg_detect.isAlive() or not poster.isAlive():
        # important thread is not running.  Exit with an error.
        sys.exit(1)
    
    # Read temperatures and update buffer index
    ad_hot[ix] = mcp.read_adc(ADC_CH_THOT)
    ad_cold[ix] = mcp.read_adc(ADC_CH_TCOLD)
    ix = (ix + 1) % BUF_LEN_TEMP

    # Check to see if it is time to log
    ts = time.time()
    if ts > next_log_ts:
        post_str = ''
        ts = int(ts)
        thot, tcold = current_temps()
        for id, val in (('heat', heat_count), ('pulse', pulse_count), ('thot', thot), ('tcold', tcold)):
            post_str += '%s\t%s_%s\t%s\n' % (ts, base_sensor_id, id, val)
        poster.publish('readings/final/btu_meter', post_str)
        if args.debug:
            print pulse_count, heat_count, current_temps()
        next_log_ts += log_interval

    time.sleep(0.05)
