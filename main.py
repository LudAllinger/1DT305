# main.py -- put your code here!
# Import from libraries
import dht
import machine
import time
import ntptime

tempSensor = dht.DHT11(machine.Pin(27))     # DHT11 Constructor 
ldr = machine.ADC(machine.Pin(26))
led = machine.Pin("LED", machine.Pin.OUT)

# Sync time with wifi
ntptime.settime()
# Add two hours to make up for the timezone
timezone = 2 * 3600

while True:
    try:
        # Current time
        ct = time.localtime(time.time() + timezone)
        # Format
        formatted_ct = "{:02}:{:02}:{:02} - {:02}/{:02}-{:04}".format(ct[3], ct[4], ct[5], ct[2], ct[1], ct[0])

        # Darkness/Light section
        tempSensor.measure()
        light = ldr.read_u16()
        darkness = round(light / 65535 * 100, 2)

        if darkness >= 70:
            print("At [{}],".format(formatted_ct))
            print("the darkness is at {}%, LED turned on".format(darkness))
            led.on()
        else:
            print("At [{}],".format(formatted_ct))
            print("The darkness is at {}%, no need to turn the LED on".format(darkness))
            led.off()

        # Temperature section
        temperature = tempSensor.temperature()
        humidity = tempSensor.humidity()
        print("Temperature is {} degrees Celsius and Humidity is {}%".format(temperature, humidity) + "\n")

        # Pause for 10 minutes
        time.sleep(600)

    except Exception as error:
        print("Exception occurred", error)
