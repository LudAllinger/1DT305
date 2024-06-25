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
import urequests

# BEGIN SETTINGS
# These need to be change to suit your environment
SEND_INTERVAL = 600000    # milliseconds
last_sent_ticks = 0  # milliseconds

tempSensor = dht.DHT11(machine.Pin(27))     # DHT11 Constructor 
ldr = machine.ADC(machine.Pin(26))

previous_darkness_values = []
values = 6

def send_data():
    global previous_darkness_values

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

        discord_message_param(temperature, humidity, darkness)

        previous_darkness_values.append(darkness)
        print("Values: ", previous_darkness_values)
        if len(previous_darkness_values) > values:
            previous_darkness_values.pop(0)
        
        if len(previous_darkness_values) == values:
            average_darkness = sum(previous_darkness_values) / values
            if darkness > average_darkness + 10:
                discord_message("Its getting brighter")
            if darkness < average_darkness - 10:
                discord_message("Its getting darker")

    except Exception as e:
        print("Sending sensor data failed: ", e)

def discord_message(message):
    send = {"content": message}
    try:
        response = urequests.post(keys.DISCORD_WEBHOOK, json=send)
        response.close()
        print(f"Discord message sent: {message}")
    except Exception as e:
        print(f"Discord message failed: {e}")

def discord_message_param(temp, humid, dark):
    send = {"content": f"Temperature: {temp} degrees, Humidity: {humid}%, Darkness: {dark}"}
    try:
        response = urequests.post(keys.DISCORD_WEBHOOK, json=send)
        response.close()
        print(f"Discord message sent: Temperature: {temp} degrees, Humidity: {humid}%, Darkness:{dark}")
    except Exception as e:
        print(f"Discord message failed: {e}")


# Try WiFi Connection
try:
    ip = boot.connect()
except KeyboardInterrupt:
    print("Keyboard interrupt")

# Use the MQTT protocol to connect to Adafruit IO
client = MQTTClient(keys.AIO_CLIENT_ID, keys.AIO_SERVER, keys.AIO_PORT, keys.AIO_USER, keys.AIO_KEY)

# Subscribed messages will be delivered to this callback

try:
    client.connect()
    print("Connected to {keys.AIO_SERVER}")

    # Sync time with wifi
    ntptime.settime()
    # Add two hours to make up for the timezone
    timezone = 2 * 3600
    while True:
        try:
            client.check_msg()

        except OSError as e:
            print(f"Check_msg failed {e}")
            try:
                client.disconnect()
                client.connect()
            except Exception as e:
                print(f"Reconnection failed {e}")
                time.sleep(10)

        client.check_msg()

        # Current time
        ct = time.localtime(time.time() + timezone)
        # Format
        formatted_ct = "{:02}:{:02}:{:02} - {:02}/{:02}-{:04}".format(ct[3], ct[4], ct[5], ct[2], ct[1], ct[0])

        if (time.ticks_ms() - last_sent_ticks) >= SEND_INTERVAL:
            send_data()
            last_sent_ticks = time.ticks_ms()

finally:
    client.disconnect()
    client = None
    boot.disconnect()
    print("Disconnected from Adafruit IO.")