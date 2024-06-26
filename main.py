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
SEND_INTERVAL_AIO = 600000    # milliseconds (10 min)
SEND_INTERVAL_DISC = 3600000  # millisecods (1 hour)
last_sent_ticks_aio = 0  # milliseconds
last_sent_ticks_disc = 0  # milliseconds

tempSensor = dht.DHT11(machine.Pin(27))     # DHT11 Constructor 
ldr = machine.ADC(machine.Pin(26))

# Hold previous values
prev_dark_values = []
prev_temp = None
prev_humid = None
prev_dark = None

# Add all values from the past hour
values = 6

# To make the "sun is rising/setting" message only appear once a day
sunrise_message = False

def send_data_aio():
    global prev_dark_values, sunrise_message

    try:
        # Collect data
        tempSensor.measure()
        temperature = tempSensor.temperature()
        humidity = tempSensor.humidity()
        light = ldr.read_u16()
        darkness = round(light / 65535 * 100, 2)

        # Sending data to Adafruit
        print(f"Sending the temperature: {temperature} degrees to {keys.AIO_TEMP_FEED}")
        client.publish(topic=keys.AIO_TEMP_FEED, msg=str(temperature))

        print(f"Sending the humidity: {humidity}% to {keys.AIO_HUMID_FEED}")
        client.publish(topic=keys.AIO_HUMID_FEED, msg=str(humidity))

        print(f"Sending the darkness: {darkness}% to {keys.AIO_DARK_FEED}")
        client.publish(topic=keys.AIO_DARK_FEED, msg=str(darkness))

        # Add darkness valus to list
        prev_dark_values.append(darkness)
        print("Values: ", prev_dark_values)
        # If there are now more values than 6, remove the first
        if len(prev_dark_values) > values:
            prev_dark_values.pop(0)
        
        if len(prev_dark_values) == values:
            # Average darkness the past hour
            average_darkness = sum(prev_dark_values) / values
            # If the darkness has fallen significantly is the last hour = Sunrise
            if darkness < average_darkness - 9 and not sunrise_message:
                discord_message("Sun is rising")
                sunrise_message = True
                # If the darkness has risen significantly is the last hour = Sunset
            elif darkness > average_darkness + 15 and sunrise_message:
                discord_message("Sun is setting")
                sunrise_message = False

    except Exception as e:
        print("Sending sensor data failed: ", e)


def send_data_disc():
    global prev_temp, prev_humid, prev_dark

    try:
        # Collect data
        tempSensor.measure()
        temperature = tempSensor.temperature()
        humidity = tempSensor.humidity()
        light = ldr.read_u16()
        darkness = round(light / 65535 * 100, 2)

        # If it has something to compare
        if prev_temp is not None and prev_humid is not None and prev_dark is not None:
            diff_temp = temperature - prev_temp
            diff_humid = humidity - prev_humid
            diff_dark = darkness - prev_dark
            discord_message_param(temperature, humidity, darkness, diff_temp, diff_humid, diff_dark)

        # Update previous values
        prev_temp = temperature
        prev_humid = humidity
        prev_dark = darkness
    
    except Exception as e:
        print("Discord data with prev has failed: ", e)

# The sunrise/sunset message
def discord_message(message):
    send = {"content": message}
    try:
        response = urequests.post(keys.DISCORD_WEBHOOK, json=send)
        response.close()
        print(f"Discord message sent: {message}")
    except Exception as e:
        print(f"Discord message failed: {e}")

# Climate update every hour
def discord_message_param(temp, humid, dark, diff_temp, diff_humid, diff_dark):
    change = []

    if diff_temp < 0:
        change.append(f"-Temperature is {temp} degrees, with an increase of {diff_temp} degrees")
    elif diff_temp > 0:
        change.append(f"-Temperature is {temp} degrees, with a decrease of {diff_temp} degrees")
    else:
        change.append(f"-Temperature is {temp} degrees, same as before")

    if diff_humid < 0:
        change.append(f"-Humidity is {humid}%, with an increase of {diff_humid}%-points")
    elif diff_humid > 0:
        change.append(f"-Humidity is {humid}%, with a decrease of {diff_humid}%-points")
    else:
        change.append(f"-Humidity is {humid}%, same as before")

    if diff_dark > 0:
        change.append(f"-Darkness is {dark}%, with an increase of {diff_dark}%-points")
    elif diff_dark < 0:
        change.append(f"-Darkness is {dark}%, with a decrease of {diff_dark}%-points")
    else:
        change.append(f"-Darkness is {dark}%, same as before")
    
    message = "Since the last hour:\n" + "\n".join(change)

    send = {
        "content": message
        }
    
    try:
        response = urequests.post(keys.DISCORD_WEBHOOK, json=send)
        response.close()

    except Exception as e:
        print(f"Discord message failed: {e}")


# Try WiFi Connection
try:
    ip = boot.connect()
except KeyboardInterrupt:
    print("Keyboard interrupt")

# Use the MQTT protocol to connect to Adafruit IO
client = MQTTClient(keys.AIO_CLIENT_ID, keys.AIO_SERVER, keys.AIO_PORT, keys.AIO_USER, keys.AIO_KEY)

try:
    client.connect()
    print("Connected to {keys.AIO_SERVER}")
    while True:
        try:
            client.check_msg()
            time.sleep(1)

        # If an error occurs, try to reconnect
        except OSError as e:
            print(f"Check_msg failed {e}")
            try:
                client.disconnect()
                client.connect()
            except Exception as e:
                print(f"Reconnection failed {e}")
                time.sleep(10)
        
        current_ticks = time.ticks_ms()

        # Adafruit interval
        if (current_ticks - last_sent_ticks_aio) >= SEND_INTERVAL_AIO:
            send_data_aio()
            last_sent_ticks_aio = current_ticks
        
        # Discord interval
        if (current_ticks - last_sent_ticks_disc) >= SEND_INTERVAL_DISC:
            send_data_disc()
            last_sent_ticks_disc = current_ticks

finally:
    client.disconnect()
    client = None
    print("Disconnected from Adafruit IO.")