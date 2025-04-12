import tkinter as tk
import math
import random
import time
import serial
import serial.tools.list_ports

# Radar GUI setup
root = tk.Tk()
root.title("Radar System with Box Control")
# Increase canvas size to accommodate more information
canvas = tk.Canvas(root, width=700, height=600, bg="black")
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
CENTER_X, CENTER_Y = 300, 300  # Center point moved to accommodate larger screen
RADIUS = 250  # Increased radar radius
canvas.create_oval(CENTER_X - RADIUS, CENTER_Y - RADIUS, 
                   CENTER_X + RADIUS, CENTER_Y + RADIUS, outline="green", tags="background")

# Keep track of the dynamic targets
targets = []
target_velocities = []  # Store velocity vectors for each target
target_visibilities = []  # Track if targets are visible or not
target_disappear_times = []  # Track when each target disappeared
target_names = []  # Store names for each target
target_types = []  # Store the type of each target (aircraft, ship, vehicle, unknown)
locked_target_index = None  # Store the index of the locked target
lock_time = None
lock_lost_time = None  # Track when a lock was lost

# Flag to indicate if initial targets have been created
initial_targets_created = False
# Number of initial targets to create
INITIAL_TARGET_COUNT = 6

# List of realistic target names for different types of aircraft, ships, and vehicles
aircraft_names = ["Eagle-1", "Raptor-2", "Falcon-3", "Hawk-4", "Viper-5", "Hornet-6", "Condor-7", "Phoenix-8"]
ship_names = ["Nimbus", "Poseidon", "Triton", "Kraken", "Tempest", "Nautilus", "Aegis", "Trident"]
vehicle_names = ["Rover-1", "Chariot-2", "Nomad-3", "Voyager-4", "Pathfinder", "Sentinel", "Guardian", "Vanguard"]
unknown_names = ["Unknown-A", "Unknown-B", "Unknown-C", "Unknown-D", "Unknown-E", "Unknown-F", "Unknown-G", "Unknown-H"]

# Target type constants
TARGET_AIRCRAFT = "aircraft"
TARGET_SHIP = "ship"
TARGET_VEHICLE = "vehicle"
TARGET_UNKNOWN = "unknown"

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
                target_name = target_names[locked_target_index] if locked_target_index < len(target_names) else "Unknown"
                print(f"Locked onto {target_name} at angle: {targets[locked_target_index][0]:.2f}°, distance: {targets[locked_target_index][1]:.2f} cm")
            else:
                locked_target_index = None
                print("No target within range")
        else:
            print("No targets available")

# Bind the key press event
root.bind("<Key>", handle_key)

# Function to create initial targets
def create_initial_targets():
    global targets, target_velocities, target_visibilities, target_names, target_types, initial_targets_created
    
    # Create 2 aircraft (far targets)
    for _ in range(2):
        angle = random.uniform(0, 180)
        distance = random.uniform(RADIUS * 0.7, RADIUS * 0.9)  # Far distance
        targets.append((angle, distance))
        # Slower velocity for aircraft (reduced by 50%)
        target_velocities.append((random.uniform(-0.5, 0.5), random.uniform(-1, 1)))
        target_visibilities.append(True)
        target_disappear_times.append(None)  # No disappear time initially
        target_names.append(random.choice(aircraft_names))
        target_types.append(TARGET_AIRCRAFT)
    
    # Create 2 ships (medium distance)
    for _ in range(2):
        angle = random.uniform(0, 180)
        distance = random.uniform(RADIUS * 0.4, RADIUS * 0.6)  # Medium distance
        targets.append((angle, distance))
        # Slower velocity for ships (reduced by 70%)
        target_velocities.append((random.uniform(-0.3, 0.3), random.uniform(-0.6, 0.6)))
        target_visibilities.append(True)
        target_disappear_times.append(None)  # No disappear time initially
        target_names.append(random.choice(ship_names))
        target_types.append(TARGET_SHIP)
    
    # Create 2 vehicles (close targets)
    for _ in range(2):
        angle = random.uniform(0, 180)
        distance = random.uniform(RADIUS * 0.1, RADIUS * 0.3)  # Close distance
        targets.append((angle, distance))
        # Slower velocity for vehicles (reduced by 80%)
        target_velocities.append((random.uniform(-0.2, 0.2), random.uniform(-0.4, 0.4)))
        target_visibilities.append(True)
        target_disappear_times.append(None)  # No disappear time initially
        target_names.append(random.choice(vehicle_names))
        target_types.append(TARGET_VEHICLE)
    
    initial_targets_created = True
    print(f"Created {len(targets)} initial targets")

# Function to update the radar display
def update_radar():
    global targets, target_velocities, target_visibilities, locked_target_index, lock_lost_time, initial_targets_created
    
    canvas.delete("target")  # Clear previous targets only
    canvas.delete("info")    # Clear info text
    canvas.delete("lock_info")  # Clear lock information

    # Create initial targets if they haven't been created yet
    if not initial_targets_created:
        create_initial_targets()
    
    # Update existing target positions based on their velocities
    for i in range(len(targets)):
        # Ensure all arrays are properly initialized and have the same length
        while len(target_velocities) <= i:
            target_velocities.append((random.uniform(-0.3, 0.3), random.uniform(-0.6, 0.6)))
            
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
        
        # Randomly toggle visibility (0.1% chance per update - 10x less frequent)
        if random.random() < 0.001 and i < len(target_visibilities):
            # If target is currently visible, make it disappear
            if target_visibilities[i]:
                target_visibilities[i] = False
                if i < len(target_disappear_times):
                    target_disappear_times[i] = time.time()  # Record when it disappeared
                else:
                    # Ensure array is properly sized
                    while len(target_disappear_times) <= i:
                        target_disappear_times.append(None)
                    target_disappear_times[i] = time.time()
                
                # If this is the locked target and it disappeared, start counting lost time
                if i == locked_target_index and lock_lost_time is None:
                    lock_lost_time = time.time()
        
        # Check if a disappeared target should reappear (after 5 seconds)
        if i < len(target_visibilities) and i < len(target_disappear_times) and not target_visibilities[i] and target_disappear_times[i] is not None:
            if time.time() - target_disappear_times[i] > 5:  # 5 seconds timeout
                target_visibilities[i] = True
                target_disappear_times[i] = None  # Reset disappear time
                
                # If this is the locked target and it reappeared, reset lost time
                if i == locked_target_index:
                    lock_lost_time = None

    # Check if lock has been lost for too long (3 seconds)
    if locked_target_index is not None and lock_lost_time is not None:
        if time.time() - lock_lost_time > 3:
            print("Lock lost - target out of radar range for too long")
            locked_target_index = None
            lock_lost_time = None
            
    # No new targets will be created - we only use the 6 initial targets

    # Draw all targets
    for i, (angle, distance) in enumerate(targets):
        # Ensure all arrays are properly initialized and have the same length
        while len(target_visibilities) <= i:
            target_visibilities.append(True)
        while len(target_disappear_times) <= i:
            target_disappear_times.append(None)
        while len(target_types) <= i:
            target_types.append(TARGET_UNKNOWN)
        while len(target_names) <= i:
            target_names.append(f"Unknown-{i+1}")
            
        # Calculate x and y based on angle and distance for all targets
        rad_angle = math.radians(angle)
        x = CENTER_X + distance * math.cos(rad_angle)
        y = CENTER_Y + distance * math.sin(rad_angle)

        # Get target type and name
        target_type = target_types[i]
        target_name = target_names[i]
        
        # Only draw visible targets on the radar
        if target_visibilities[i]:
            # Draw the radar target with different icons based on type
            if locked_target_index is not None and i == locked_target_index:
                # Highlight the locked target with yellow outline
                canvas.create_oval(x-10, y-10, x+10, y+10, outline="yellow", width=2, tags="target")
                
                # Draw different icons based on target type
                if target_type == TARGET_AIRCRAFT:
                    # Aircraft - triangle pointing up
                    canvas.create_polygon(x, y-7, x-6, y+5, x+6, y+5, fill="red", outline="white", tags="target")
                elif target_type == TARGET_SHIP:
                    # Ship - diamond shape
                    canvas.create_polygon(x, y-7, x+7, y, x, y+7, x-7, y, fill="blue", outline="white", tags="target")
                elif target_type == TARGET_VEHICLE:
                    # Vehicle - square
                    canvas.create_rectangle(x-5, y-5, x+5, y+5, fill="green", outline="white", tags="target")
                else:
                    # Unknown - circle
                    canvas.create_oval(x-5, y-5, x+5, y+5, fill="orange", tags="target")
                    
                # Show target name near the locked target with background for better visibility
                text_bg = canvas.create_rectangle(x-60, y-25, x+60, y-10, fill="black", outline="yellow", tags="target")
                canvas.create_text(x, y-17, text=target_name, fill="yellow", tags="target")
            else:
                # Draw different icons based on target type (non-locked)
                if target_type == TARGET_AIRCRAFT:
                    # Aircraft - triangle pointing up
                    canvas.create_polygon(x, y-5, x-5, y+3, x+5, y+3, fill="red", tags="target")
                elif target_type == TARGET_SHIP:
                    # Ship - diamond shape
                    canvas.create_polygon(x, y-5, x+5, y, x, y+5, x-5, y, fill="blue", tags="target")
                elif target_type == TARGET_VEHICLE:
                    # Vehicle - square
                    canvas.create_rectangle(x-4, y-4, x+4, y+4, fill="green", tags="target")
                else:
                    # Unknown - circle
                    canvas.create_oval(x-5, y-5, x+5, y+5, fill="orange", tags="target")
                
                # Show name next to all targets with semi-transparent background
                # Calculate position based on angle to prevent text from overlapping with radar edge
                text_angle = angle
                if 45 <= angle <= 135:  # Top half of radar
                    text_y = y - 15
                    text_x = x
                elif angle < 45:  # Right side
                    text_y = y
                    text_x = x + 15
                else:  # Left side
                    text_y = y
                    text_x = x - 15
                
                # Create background for text
                name_width = len(target_name) * 4 + 10  # Approximate width based on text length
                canvas.create_rectangle(text_x-name_width/2, text_y-8, text_x+name_width/2, text_y+8, 
                                        fill="black", outline="", tags="target")
                canvas.create_text(text_x, text_y, text=target_name, fill="cyan", tags="target")

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
    target_info_x = 570  # Move it more to the right for larger screen
    canvas.create_text(target_info_x, 10, text="Target Info", fill="white", anchor="w", tags="info")
    
    # Only show info for the 5 most recent targets to avoid overflow
    # Only include targets that are currently visible
    visible_targets = [(i, target) for i, target in enumerate(targets) 
                      if i < len(target_visibilities) and target_visibilities[i]]
    
    # Sort by distance (closest first)
    visible_targets.sort(key=lambda x: x[1][1])
    
    # Display only up to 5 targets
    for display_idx, (i, (angle, distance)) in enumerate(visible_targets[:5]):
        # Get target name and type or use defaults if not available
        target_name = target_names[i] if i < len(target_names) else f"Unknown-{i+1}"
        target_type = target_types[i] if i < len(target_types) else TARGET_UNKNOWN
        
        # Add icon symbol based on target type
        type_symbol = "▲" if target_type == TARGET_AIRCRAFT else "◆" if target_type == TARGET_SHIP else "■" if target_type == TARGET_VEHICLE else "●"
        target_text = f"{type_symbol} {target_name}: {angle:.0f}°, {distance:.0f}cm"
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
        
        # Get target name and type
        target_name = target_names[locked_target_index] if locked_target_index < len(target_names) else "Unknown"
        target_type = target_types[locked_target_index] if locked_target_index < len(target_types) else TARGET_UNKNOWN
        
        # Get type description
        type_desc = "Aircraft" if target_type == TARGET_AIRCRAFT else "Ship" if target_type == TARGET_SHIP else "Vehicle" if target_type == TARGET_VEHICLE else "Unknown"
        
        # Only draw the targeting line if the target is currently visible
        if locked_target_index < len(target_visibilities) and target_visibilities[locked_target_index]:
            canvas.create_text(lock_x, lock_y - 45, text=f"TARGET: {target_name}", 
                              fill="yellow", anchor="w", tags="lock_info")
            canvas.create_text(lock_x, lock_y - 30, text=f"TYPE: {type_desc}", 
                              fill="yellow", anchor="w", tags="lock_info")
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
        
    # Refresh every 150ms (0.15 seconds) - slightly slower refresh rate for smoother movement
    root.after(150, update_radar)

# Start updating the radar
update_radar()
root.mainloop()
