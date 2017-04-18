#!/usr/bin/python
"""Script to implement a single channel pulse counter that
posts to the mini-monitor MQTT broker.
"""
import time
import sys
import input_change
import mqtt_poster

# Access some settings in the Mini-Monitor settings file
# The settings file is installed in the FAT boot partition of the Pi SD card,
# so that it can be easily configured from the PC that creates the SD card.  
# Include that directory in the Path so the settings file can be found.
sys.path.insert(0, '/boot/pi_logger')
import settings

