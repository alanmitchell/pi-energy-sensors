#!/usr/bin/python
import threading
import time
import RPi.GPIO as GPIO

class InputChange(threading.Thread):

    def __init__(self, pins, call_back, pull_up=False, read_gap=3.0, buffer_len=8, debug_pin=None):
        """Class to detect changes in a set of input pins.  Each pin is debounced by looking
        for a stable set of readings of the new state to occur.  After 'buffer_len' readings
        of the new state, spaced 'read_gap' milliseconds apart, a transition is deemed to 
        have occurred.
        Constructor parameters are:
            pins              list of pin numbers (BCM) to detect transitions on
            call_back         function to call when a transition occurs.  The pin number, 
                                  and the new pin state,True or False, are passed as 
                                  parameters to the function.
            pull_up           if True, turn on the internal Raspberry Pi pullup for the pins
            read_gap          number of milliseconds between reads of the input pins
            buffer_len        number of stable reads required before a transition is deemed
            debug_pin         pin number to toggle at every point a set of input pin reads occur
        """

        # run constructor of base class
        threading.Thread.__init__(self)
        self.daemon = True     # Python should exit if only this thread is left

        try:
            len(pins)
            self.pins = pins               # pin numbers (BCM) to detect pulses on
        except:
            self.pins = [pins]             # assume that one pin number was passed; convert to list
        self.call_back = call_back         # function to call when pulse occurs
        self.read_gap = read_gap           # milliseconds of gap between readings of input
        self.buffer_len = buffer_len       # number of readings required to declare new state
        self.debug_pin = debug_pin         # pin to toggle at each read. If None, no toggle

        # Set up GPIO module and input pins
        GPIO.setmode(GPIO.BCM)
        for pin in self.pins:
            if pull_up:
                GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            else:
                GPIO.setup(pin, GPIO.IN)

        if debug_pin:
            GPIO.setup(debug_pin, GPIO.OUT)

    def run(self):

        # these dictionaries are keyed on pin number
        cur_state = {}
        state_reads = {}
        for pin in self.pins:
            # initialize both current and buffer to current pin state
            cur_state[pin] = GPIO.input(pin)
            state_reads[pin] = [cur_state[pin]] * self.buffer_len
        debug_state = False

        ix = 0

        while True:

            for pin in self.pins:

                state_reads[pin][ix] = GPIO.input(pin)

                if sum(state_reads[pin]) == (not cur_state[pin]) * self.buffer_len:
                    # a state change occurred; record it and call
                    # the callback function.
                    cur_state[pin] = not cur_state[pin]
                    self.call_back(pin, cur_state[pin])

            ix = (ix + 1) % self.buffer_len

            if self.debug_pin:
                debug_state = not debug_state
                GPIO.output(self.debug_pin, debug_state)

            time.sleep(self.read_gap / 1000.0)

if __name__=='__main__':

    # Test routine and usage example

    ct = 0
    def chg(pin_num, new_state):
        global ct
        if pin_num==18:
            ct += 1
        elif pin_num==23:
            print 'Pin %s: %s' % (pin_num, new_state)

    pchg = InputChange([18, 23], chg, pull_up=True, debug_pin=16)

    pchg.start()

    while True:
        time.sleep(10)
        print ct
