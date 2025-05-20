#hardware.py
import gpiod
from gpiod.line import Direction, Value

def set_gpio17(value):
    """
    Sets GPIO pin 17 to the specified value (ACTIVE or INACTIVE).
    """
    with gpiod.request_lines(
        "/dev/gpiochip0",
        consumer="gpio_control",
        config={
            17: gpiod.LineSettings(
            direction=Direction.OUTPUT,
            output_value=value
            )
        }
    ) as request:
        request.set_value(17, value)

def toggle_gpio17(current_mode):
    """
    Toggles GPIO17 between ON and OFF states.
    Returns the new mode as a string.
    """
    if current_mode == 'OFF':
        set_gpio17(Value.ACTIVE)
        return 'ON'
    else:
        set_gpio17(Value.INACTIVE)
        return 'OFF'
