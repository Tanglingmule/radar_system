from machine import Pin, UART
import time

# UART0 is used for onboard USB serial communication
uart = UART(0, baudrate=9600)

# Ultrasonic sensor pins
TRIG = Pin(2, Pin.OUT)
ECHO = Pin(3, Pin.IN)

# Function to measure distance
def measure_distance():
    TRIG.low()
    time.sleep_us(2)
    TRIG.high()
    time.sleep_us(10)
    TRIG.low()
    
    while ECHO.value() == 0:
        start = time.ticks_us()
    
    while ECHO.value() == 1:
        end = time.ticks_us()
    
    duration = time.ticks_diff(end, start)
    distance = (duration * 0.0343) / 2  # Convert to cm
    return distance

# Main loop
while True:
    print("Starting to send data...")  # Debug: Check if loop starts
    
    distance = measure_distance()
    
    # Format the data as angle and distance
    angle = 90  # Just an example angle for now (could be dynamic based on your servo)
    data = f"{angle},{distance}\n"
    
    print(f"Sending data: {data}")  # Debug: Check what is being sent
    
    # Send data via UART (USB serial)
    uart.write(data)
    
    # Add a small delay to avoid flooding the serial port
    time.sleep(1)
