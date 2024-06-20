# main.py -- put your code here!
# Import from libraries
import dht
import time
from mqtt import MQTTClient
import machine
import micropython
import keys
import boot
import ntptime

# BEGIN SETTINGS
# These need to be change to suit your environment
SEND_INTERVAL = 600000    # milliseconds
last_sent_ticks = 0  # milliseconds

tempSensor = dht.DHT11(machine.Pin(27))     # DHT11 Constructor 
ldr = machine.ADC(machine.Pin(26))

def send_data():
    try:
        tempSensor.measure()
        temperature = tempSensor.temperature()
        humidity = tempSensor.humidity()
        light = ldr.read_u16()
        darkness = round(light / 65535 * 100, 2)

        print(f"Sending the temperature: {temperature} degrees to {keys.AIO_TEMP_FEED}")
        client.publish(topic=keys.AIO_TEMP_FEED, msg=str(temperature))

        print(f"Sending the humidity: {humidity}% to {keys.AIO_HUMID_FEED}")
        client.publish(topic=keys.AIO_HUMID_FEED, msg=str(humidity))

        print(f"Sending the darkness: {darkness}% to {keys.AIO_DARK_FEED}")
        client.publish(topic=keys.AIO_DARK_FEED, msg=str(darkness))

    except Exception as e:
        print("Sending sensor data failed: ", e)


# Try WiFi Connection
try:
    ip = boot.connect()
except KeyboardInterrupt:
    print("Keyboard interrupt")

# Use the MQTT protocol to connect to Adafruit IO
client = MQTTClient(keys.AIO_CLIENT_ID, keys.AIO_SERVER, keys.AIO_PORT, keys.AIO_USER, keys.AIO_KEY)

# Subscribed messages will be delivered to this callback
client.connect()
print("Connected to {keys.AIO_SERVER}")

# Sync time with wifi
ntptime.settime()
# Add two hours to make up for the timezone
timezone = 2 * 3600

try:
    while True:
        client.check_msg()

        # Current time
        ct = time.localtime(time.time() + timezone)
        # Format
        formatted_ct = "{:02}:{:02}:{:02} - {:02}/{:02}-{:04}".format(ct[3], ct[4], ct[5], ct[2], ct[1], ct[0])

        if (time.ticks_ms() - last_sent_ticks) >= SEND_INTERVAL:
            send_data()
            last_sent_ticks = time.ticks_ms()
        
        time.sleep(600)

finally:
    client.disconnect()
    client = None
    boot.disconnect()
    print("Disconnected from Adafruit IO.")