import tkinter as tk
import math
import random
import time
import serial
import serial.tools.list_ports

# Radar GUI setup
root = tk.Tk()
root.title("Radar System with Box Control")
canvas = tk.Canvas(root, width=400, height=400, bg="black")
canvas.pack()

# Try to find available serial ports
available_ports = list(serial.tools.list_ports.comports())
ser = None

# Try to connect to the first available port
if available_ports:
    try:
        ser = serial.Serial(available_ports[0].device, baudrate=9600, timeout=1)
        print(f"Connected to {available_ports[0].device}")
    except Exception as e:
        print(f"Could not connect to {available_ports[0].device}: {e}")
        ser = None
else:
    print("No serial ports found")

# Draw radar background (static, no need to redraw every time)
CENTER_X, CENTER_Y = 200, 200
RADIUS = 180
canvas.create_oval(CENTER_X - RADIUS, CENTER_Y - RADIUS, 
                   CENTER_X + RADIUS, CENTER_Y + RADIUS, outline="green", tags="background")

# Keep track of the dynamic targets
targets = []
target_velocities = []  # Store velocity vectors for each target
target_visibilities = []  # Track if targets are visible or not
locked_target_index = None  # Store the index of the locked target
lock_time = None
lock_lost_time = None  # Track when a lock was lost

# Create a movable box
box_size = 20
box_x, box_y = CENTER_X, CENTER_Y
# Create only the left and right sides of the box with white lines
left_line = canvas.create_line(box_x - box_size // 2, box_y - box_size // 2, 
                              box_x - box_size // 2, box_y + box_size // 2, 
                              fill="white", tags="box")
right_line = canvas.create_line(box_x + box_size // 2, box_y - box_size // 2, 
                               box_x + box_size // 2, box_y + box_size // 2, 
                               fill="white", tags="box")

# Function to move the box
def move_box(dx, dy):
    global box_x, box_y
    # Update box position
    box_x += dx
    box_y += dy
    # Keep the box within the radar circle
    distance_from_center = math.sqrt((box_x - CENTER_X)**2 + (box_y - CENTER_Y)**2)
    if distance_from_center > RADIUS - box_size // 2:
        # If box is outside the radar, adjust position
        angle = math.atan2(box_y - CENTER_Y, box_x - CENTER_X)
        box_x = CENTER_X + (RADIUS - box_size // 2) * math.cos(angle)
        box_y = CENTER_Y + (RADIUS - box_size // 2) * math.sin(angle)
    # Redraw the box at the new position (only left and right sides)
    canvas.coords(left_line, box_x - box_size // 2, box_y - box_size // 2, 
                 box_x - box_size // 2, box_y + box_size // 2)
    canvas.coords(right_line, box_x + box_size // 2, box_y - box_size // 2, 
                 box_x + box_size // 2, box_y + box_size // 2)

# Bind keyboard events to move the box
def handle_key(event):
    global locked_target_index, lock_time
    key = event.keysym.lower()
    if key == 'w':
        move_box(0, -10)  # Move up
    elif key == 's':
        move_box(0, 10)   # Move down
    elif key == 'a':
        move_box(-10, 0)  # Move left
    elif key == 'd':
        move_box(10, 0)   # Move right
    elif key == 'space':
        # Find the closest target to the box
        if targets:
            closest_target_idx = None
            min_distance = float('inf')
            for i, target in enumerate(targets):
                angle, distance = target
                rad_angle = math.radians(angle)
                target_x = CENTER_X + distance * math.cos(rad_angle)
                target_y = CENTER_Y + distance * math.sin(rad_angle)
                
                # Calculate distance between box and target
                box_to_target = math.sqrt((box_x - target_x)**2 + (box_y - target_y)**2)
                
                if box_to_target < min_distance:
                    min_distance = box_to_target
                    closest_target_idx = i
            
            # Lock onto the closest target if it's within range (50 pixels)
            if min_distance < 50:
                locked_target_index = closest_target_idx
                lock_time = time.time()
                print(f"Locked onto target at angle: {targets[locked_target_index][0]:.2f}°, distance: {targets[locked_target_index][1]:.2f} cm")
            else:
                locked_target_index = None
                print("No target within range")
        else:
            print("No targets available")

# Bind the key press event
root.bind("<Key>", handle_key)

# Function to update the radar display
def update_radar():
    global targets, target_velocities, target_visibilities, locked_target_index, lock_lost_time
    
    canvas.delete("target")  # Clear previous targets only
    canvas.delete("info")    # Clear info text
    canvas.delete("lock_info")  # Clear lock information

    # Update existing target positions based on their velocities
    for i in range(len(targets)):
        if i < len(target_velocities):  # Make sure we have velocity for this target
            angle, distance = targets[i]
            v_angle, v_distance = target_velocities[i]
            
            # Update angle and distance based on velocity
            new_angle = (angle + v_angle) % 180
            new_distance = distance + v_distance
            
            # Bounce off boundaries
            if new_distance <= 0 or new_distance >= RADIUS:
                target_velocities[i] = (v_angle, -v_distance)
                new_distance = max(0, min(new_distance, RADIUS))
            
            # Update target position
            targets[i] = (new_angle, new_distance)
            
            # Randomly toggle visibility (1% chance per update) but don't delete targets
            if random.random() < 0.01:
                target_visibilities[i] = not target_visibilities[i]
                
                # If this is the locked target and it disappeared, start counting lost time
                if i == locked_target_index and not target_visibilities[i]:
                    if lock_lost_time is None:
                        lock_lost_time = time.time()
                # If this is the locked target and it reappeared, reset lost time
                elif i == locked_target_index and target_visibilities[i]:
                    lock_lost_time = None

    # Check if lock has been lost for too long (3 seconds)
    if locked_target_index is not None and lock_lost_time is not None:
        if time.time() - lock_lost_time > 3:
            print("Lock lost - target out of radar range for too long")
            locked_target_index = None
            lock_lost_time = None

    if ser and ser.is_open:
        try:
            if ser.in_waiting > 0:
                line = ser.readline().decode().strip()
                
                if "Sending data:" in line:
                    # Extract just the numeric data after "Sending data:"
                    line = line.split("Sending data:")[-1].strip()
                
                if "," in line:  # Ensure the data contains a comma separating angle and distance
                    parts = line.split(",")
                    if len(parts) >= 2:
                        try:
                            angle = float(parts[0])
                            distance = float(parts[1])
                            
                            # Scale the distance to fit within the radar's range (up to RADIUS)
                            if distance > RADIUS:
                                distance = RADIUS  # Clip distance to the radar's radius for visibility
                                
                            # Only add new targets if we have fewer than MAX_TARGETS
                            if len(targets) < 15:  # Increased max targets to 15
                                targets.append((angle, distance))
                                # Add a random velocity for this target
                                target_velocities.append((random.uniform(-1, 1), random.uniform(-2, 2)))
                                # Start as visible
                                target_visibilities.append(True)
                        except ValueError:
                            print(f"Invalid data format: {line}")
        except Exception as e:
            print(f"Error reading serial: {e}")
    else:
        # If no serial connection, generate simulated data occasionally
        if random.random() < 0.03 and len(targets) < 15:  # Only add if fewer than max targets
            angle = random.uniform(0, 180)
            distance = random.uniform(RADIUS * 0.3, RADIUS * 0.8)  # Start targets in middle area
            targets.append((angle, distance))
            # Add a random velocity for this target
            target_velocities.append((random.uniform(-1, 1), random.uniform(-2, 2)))
            # Start as visible
            target_visibilities.append(True)

    # Draw all targets
    for i, (angle, distance) in enumerate(targets):
        # Only draw visible targets
        if i < len(target_visibilities) and target_visibilities[i]:
            # Calculate x and y based on angle and distance
            rad_angle = math.radians(angle)
            x = CENTER_X + distance * math.cos(rad_angle)
            y = CENTER_Y + distance * math.sin(rad_angle)

            # Draw the radar target
            if locked_target_index is not None and i == locked_target_index:
                # Highlight the locked target
                canvas.create_oval(x-8, y-8, x+8, y+8, outline="yellow", width=2, tags="target")
                canvas.create_oval(x-5, y-5, x+5, y+5, fill="red", tags="target")
            else:
                canvas.create_oval(x-5, y-5, x+5, y+5, fill="red", tags="target")

    # Status info
    if ser and ser.is_open:
        status_text = "Connected"
        port_text = f"Port: {ser.name}"
        status_color = "green"
    else:
        status_text = "Simulation Mode"
        port_text = "No Serial Connection"
        status_color = "yellow"

    # Display info texts
    canvas.create_text(10, 10, text=status_text, fill=status_color, anchor="w", tags="info")
    canvas.create_text(10, 30, text=port_text, fill="white", anchor="w", tags="info")
    canvas.create_text(10, 50, text=f"Time: {time.strftime('%H:%M:%S')}", fill="white", anchor="w", tags="info")

    # Box position info
    canvas.create_text(10, 70, text=f"Box Position: ({box_x-CENTER_X:.0f}, {box_y-CENTER_Y:.0f})", 
                      fill="cyan", anchor="w", tags="info")

    # Target info to the right of the radar - ensure it fits on screen
    target_info_x = 320  # Move it a bit more to the right
    canvas.create_text(target_info_x, 10, text="Target Info", fill="white", anchor="w", tags="info")
    
    # Only show info for the 5 most recent targets to avoid overflow
    visible_targets = [(i, target) for i, target in enumerate(targets) 
                      if i < len(target_visibilities) and target_visibilities[i]]
    
    # Sort by distance (closest first)
    visible_targets.sort(key=lambda x: x[1][1])
    
    # Display only up to 5 targets
    for display_idx, (i, (angle, distance)) in enumerate(visible_targets[:5]):
        target_text = f"T{i+1}: {angle:.0f}°, {distance:.0f}cm"
        # Highlight the locked target in the list
        text_color = "yellow" if i == locked_target_index else "green"
        canvas.create_text(target_info_x, 30 + display_idx * 20, 
                          text=target_text, fill=text_color, anchor="w", tags="info")
    
    # Show count of additional targets if there are more than 5
    if len(visible_targets) > 5:
        canvas.create_text(target_info_x, 30 + 5 * 20, 
                          text=f"+ {len(visible_targets) - 5} more", 
                          fill="gray", anchor="w", tags="info")

    # Display lock information if a target is locked
    if locked_target_index is not None and locked_target_index < len(targets):
        # Get the current position of the locked target
        locked_target = targets[locked_target_index]
        
        # Calculate time since lock
        time_since_lock = time.time() - lock_time
        
        # Generate random altitude based on the distance (for simulation)
        altitude = locked_target[1] * 10  # 10 times the distance for altitude in meters
        
        # Calculate time until impact (simulated - decreases over time)
        impact_time = max(30 - time_since_lock, 0)  # Start with 30 seconds, countdown
        
        # Display lock information to the right of the box
        lock_x = box_x + box_size // 2 + 10
        lock_y = box_y
        
        # Only draw the targeting line if the target is currently visible
        if locked_target_index < len(target_visibilities) and target_visibilities[locked_target_index]:
            canvas.create_text(lock_x, lock_y - 15, text=f"LOCKED", 
                              fill="yellow", anchor="w", tags="lock_info")
            canvas.create_text(lock_x, lock_y, text=f"Alt: {altitude:.0f}m", 
                              fill="white", anchor="w", tags="lock_info")
            canvas.create_text(lock_x, lock_y + 15, text=f"Impact: {impact_time:.1f}s", 
                              fill="red", anchor="w", tags="lock_info")
            
            # Draw a targeting line from box to locked target - updates with target movement
            rad_angle = math.radians(locked_target[0])
            target_x = CENTER_X + locked_target[1] * math.cos(rad_angle)
            target_y = CENTER_Y + locked_target[1] * math.sin(rad_angle)
            canvas.create_line(box_x, box_y, target_x, target_y, 
                              fill="yellow", dash=(3, 2), tags="lock_info")
        else:
            # Target is not visible, show "TRACKING" instead of "LOCKED"
            canvas.create_text(lock_x, lock_y - 15, text=f"TRACKING...", 
                              fill="orange", anchor="w", tags="lock_info")
            canvas.create_text(lock_x, lock_y, text=f"Signal lost", 
                              fill="orange", anchor="w", tags="lock_info")
            canvas.create_text(lock_x, lock_y + 15, text=f"Reacquiring target", 
                              fill="orange", anchor="w", tags="lock_info")
        
    # Refresh every 100ms (0.1 seconds)
    root.after(100, update_radar)

# Start updating the radar
update_radar()
root.mainloop()
