# main.py -- put your code here!
# Import from libraries
import machine
import time

adc = machine.ADC(27)
sf = 4095/65535 # Scale factor
volt_per_adc = (3.3 / 4095)

while True: 
    time.sleep(1)
    millivolts = adc.read_u16()

    adc_12b = millivolts * sf

    volt = adc_12b * volt_per_adc

    # MCP9700 characteristics
    dx = abs(50 - 0)
    dy = abs(0 - 0.5)

    shift = volt - 0.5
    temp = shift / (dy / dx)
    print(temp, "degrees")
    time.sleep(1)