# main.py -- put your code here!
# Import from libraries
import dht
import machine
import time
import utime

tempSensor = dht.DHT11(machine.Pin(27))     # DHT11 Constructor 
# tempSensor = dht.DHT22(machine.Pin(27))   # DHT22 Constructor
ldr = machine.ADC(machine.Pin(26))
led = machine.Pin("LED", machine.Pin.OUT)

while True:
    try:
        tempSensor.measure()
        light = ldr.read_u16()

        darkness = round(light / 65535 * 100, 2)
        if darkness >= 70:
            print("Darkness is at {}%, LED turned on".format(darkness))
            led.on()
        else:
            print("Darkness is at {}%, no need to turn the LED on".format(darkness))
            led.off()

        temperature = tempSensor.temperature()
        humidity = tempSensor.humidity()
        print("Temperature is {} degrees Celsius and Humidity is {}%".format(temperature, humidity) +"\n")
        time.sleep(600)

    except Exception as error:
        print("Exception occurred", error)
