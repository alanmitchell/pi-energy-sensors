#!/usr/bin/python
import threading
import time
import RPi.GPIO as GPIO

class InputChange(threading.Thread):

    def __init__(self, pin_num, call_back, pull_up=False, read_gap=4.0, buffer_len=8, debug_pin=None):
        """Class to detect changes in an input pin.  The pin is debounced by looking
        for a stable set of readings of the new state to occur.  After 'buffer_len' readings
        of the new state, spaced 'read_gap' milliseconds apart, a transition is deemed to 
        have occurred.
        Constructor parameters are:
            pin_num           pin number (BCM) to detect transitions on
            call_back         function to call when a transition occurs.  The pin number, 
                                  and the new pin state,True or False, are passed as 
                                  parameters to the function.
            pull_up           if True, turn on the internal Raspberry Pi pullup for the pin
            read_gap          number of milliseconds between reads of the input pin
            buffer_len        number of stable reads required before a transition is deemed
            debug_pin         pin number to toggle at every point an input pin read occurs
        """

        # run constructor of base class
        threading.Thread.__init__(self)
        self.daemon = True     # Python should exit if only this thread is left

        self.pin_num = pin_num             # pin number (BCM) to detect pulses on
        self.call_back = call_back         # function to call when pulse occurs
        self.read_gap = read_gap           # milliseconds of gap between readings of input
        self.buffer_len = buffer_len       # number of readings required to declare new state
        self.debug_pin = debug_pin         # pin to toggle at each read. If None, no toggle

        # Set up GPIO module and input pin
        GPIO.setmode(GPIO.BCM)
        if pull_up:
            GPIO.setup(pin_num, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        else:
            GPIO.setup(pin_num, GPIO.IN)

        if debug_pin:
            GPIO.setup(debug_pin, GPIO.OUT)

    def run(self):

        state = False
        state_reads = [state] * self.buffer_len
        debug_state = False

        ix = 0

        while True:
            state_reads[ix] = GPIO.input(self.pin_num)
            ix = (ix + 1) % self.buffer_len

            if sum(state_reads) == (not state) * self.buffer_len:
                # a state change occurred; record it and call
                # the callback function.
                state = not state
                self.call_back(self.pin_num, state)

            if self.debug_pin:
                debug_state = not debug_state
                GPIO.output(self.debug_pin, debug_state)

            time.sleep(self.read_gap / 1000.0)

if __name__=='__main__':

    # Test routine

    def chg(pin_num, new_state):
        print 'Change on Pin %s: %s' % (pin_num, new_state)

    pchg = InputChange(18, chg, pull_up=True, debug_pin=16)

    pchg.start()

    while True:
        time.sleep(1)
