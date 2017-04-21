# pi-energy-sensors
Implements energy-related sensors on the Raspberry Pi, including a BTU meter and a Pulse Counter.

For the Pulse counter, the main script is `pulse_counter_1ch.py`, and the supervisor script that
starts and restarts the pulse counter script is `run_pulse_counter_1ch`.
Here are the schematic and board picture for the Pulse Counter:

![Pulse Counter Schematic](docs/images/schematic_pulse_counter.jpg)

![Pulse Counter Board Picture](docs/images/board_pulse_counter.jpg)

For the BTU meter, the main script is `btu_meter.py` and the supervisor script to start
and restart it is `run_btu_meter`.  Here are the schematic and board picture for the BTU meter:

![BTU Meter Schematic](docs/images/schematic_btu_meter.jpg)

![BTU Meter Board Picture](docs/images/board_btu_meter.jpg)
