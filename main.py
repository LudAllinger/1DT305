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
SEND_INTERVAL_AIO = 10000    # milliseconds (10 seconds)
UPDATE_DARKNESS = 600000     # milliseconds (10 minutes)
SEND_INTERVAL_DISC = 3600000  # millisecods (1 hour)

current_ticks = time.ticks_ms()
last_sent_ticks_aio = current_ticks - SEND_INTERVAL_AIO  # milliseconds
last_sent_ticks_darkness = current_ticks - UPDATE_DARKNESS  # millisecods
last_sent_ticks_disc = current_ticks - SEND_INTERVAL_DISC  # milliseconds

tempSensor = dht.DHT11(machine.Pin(27))  # DHT11 Constructor 
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

        # Check if it is getting brighter/darker
        sunrise_sunset(darkness)

        # Append darkness values every 10 minutes ofr a 1 hour total
        current_ticks = time.ticks_ms()
        if (current_ticks - last_sent_ticks_darkness) >= UPDATE_DARKNESS:
            update_darkness_list(darkness)
            last_sent_ticks_darkness = current_ticks

    except Exception as e:
        print("Sending sensor data failed: ", e)


# Saving the past 6 darkness values for a 1 hour interval
def update_darkness_list(darkness):
    # Add darkness valus to list
    prev_dark_values.append(darkness)
    print("Values before pop:", prev_dark_values)
    # If there are now more values than 6, remove the first
    if len(prev_dark_values) > values:
        prev_dark_values.pop(0)
        print("Darkness values after pop:", prev_dark_values)


# Check if it is getting brighter or darker outside
def sunrise_sunset(darkness):
    global sunrise_message
    if len(prev_dark_values) == values:
        # Average darkness the past hour
        average_darkness = sum(prev_dark_values) / values
        #NOTE: the + and - integers may need to be updated depending on your location
        # If the darkness has fallen significantly is the last hour = Sunrise   
        if darkness < average_darkness - 9 and not sunrise_message:
            discord_message("It's getting brighter")
            sunrise_message = True
            # If the darkness has risen significantly is the last hour = Sunset
        elif darkness > average_darkness + 15 and sunrise_message:
            discord_message("It's getting darker")
            sunrise_message = False


# Send data to discord every hour
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
        else:
            initial_disc_message(temperature, humidity, darkness)

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


# The first discord message upon start
def initial_disc_message(temp, humid, dark):
    send = {"content": f"At start:\n-Temperature is at {temp} degrees\n-Humidity is at {humid}%\n-Darkness is at {dark}%"}
    try:
        response = urequests.post(keys.DISCORD_WEBHOOK, json=send)
        response.close()
        print(f"Initial Discord message sent")
    except Exception as e:
        print(f"Discord message failed: {e}")


# Climate update every hour
def discord_message_param(temp, humid, dark, diff_temp, diff_humid, diff_dark):
    change = []

    # Appends the correct sentence
    if diff_temp > 0:
        change.append(f"- Temperature is at {temp} degrees, with an increase of {diff_temp:.2f} degrees")
    elif diff_temp < 0:
        change.append(f"- Temperature is at {temp} degrees, with a decrease of {abs(diff_temp):.2f} degrees")
    else:
        change.append(f"- Temperature is at {temp} degrees, same as before")

    if diff_humid > 0:
        change.append(f"- Humidity is at {humid}%, with an increase of {diff_humid:.2f} percentage points")
    elif diff_humid < 0:
        change.append(f"- Humidity is at {humid}%, with a decrease of {abs(diff_humid):.2f} percentage points")
    else:
        change.append(f"- Humidity is at {humid}%, same as before")

    if diff_dark > 0:
        change.append(f"- Darkness is at {dark}%, with an increase of {diff_dark:.3f} percentage points")
    elif diff_dark < 0:
        change.append(f"- Darkness is at {dark}%, with a decrease of {abs(diff_dark):.3f} percentage points")
    else:
        change.append(f"- Darkness is at {dark}%, same as before")
    
    # From list to string
    message = "\nSince the last hour:\n" + "\n".join(change)
    # The message that gets sent
    send = {"content": message}
    try:
        response = urequests.post(keys.DISCORD_WEBHOOK, json=send)
        response.close()
        print(f"Discord message: {message}")
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
    while True:
        try:
            client.check_msg()
        # If an error occurs, try to reconnect
        except OSError as e:
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