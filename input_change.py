import threading
import time
import RPi.GPIO as GPIO

class InputChange(threading.Thread)

    READ_GAP = 4.0  # milliseconds
    BUFFER_LEN = 8  # numbe of stable reads required

    def __init__(self, pin_num, call_back, pull_up=False):
        """Class to detect changes in an input pin.  The pin is debounced by looking
        for a stable set of readings of the new state to occur.  After BUFFER_LEN readings
        of the new state, spaced READ_GAP milliseconds apart, a transition is deemed to 
        have occurred.
        Constructor parameters are:
            pin_num           pin number (BCM) to detect transitions on
            call_back         function to call when a transition occurs.  The pin number, 
                                  and the new pin state,True or False, are passed as 
                                  parameters to the function.
            pull_up           if True, turn on the internal Raspberry Pi pullup for the pin
        """

        # run constructor of base class
        threading.Thread.__init__(self)
        self.daemon = True     # Python should exit if only this thread is left

        self.pin_num = pin_num             # pin number (BCM) to detect pulses on
        self.call_back = call_back         # function to call when pulse occurs

        # Set up GPIO module and input pin
        GPIO.setmode(GPIO.BCM)
        if pull_up:
            GPIO.setup(pin_num, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        else:
            GPIO.setup(pin_num, GPIO.IN)

    def run(self):

        state = False
        state_reads = [state] * PulseCounter.BUFFER_LEN
        ix = 0

        while True:
            state_reads[ix] = GPIO.input(self.pin_num)
            ix = (ix + 1) % PulseCounter.BUFFER_LEN

            if sum(state_reads) == (not state) * BUFFER_LEN:
                # a state change occurred; record it and call
                # the callback function.
                state = not state
                self.call_back(self.pin_num, state)

            time.sleep(PulseCounter.READ_GAP / 1000.0)
