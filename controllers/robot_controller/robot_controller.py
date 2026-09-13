"""
Robot Controller for ROBO_001 (DienBien Robot) — NhanUI Edition
- Rich STATUS JSON protocol for dashboard monitoring
- Camera streaming via base64 JPEG
- Mimic joint synchronization for parallel linkage mechanism
- Manual control commands (movement, arm, gripper) from dashboard
- Sim-to-Real bridge integration for hardware robot control
"""

from controller import Supervisor
import sys
import time
import json
import base64

# Sim-to-Real bridge (imported safely — won't crash if websockets missing)
try:
    from sim2real_client import HardwareBridge, get_bridge
    hw_bridge = get_bridge()
except Exception:
    hw_bridge = None

robot = Supervisor()
timeStep = int(robot.getBasicTimeStep())
robot_node = robot.getSelf()
robot_name = robot.getName()

# Save initial pose for soft reset
translation_field = robot_node.getField("translation") if robot_node else None
rotation_field = robot_node.getField("rotation") if robot_node else None
initial_translation = list(translation_field.getSFVec3f()) if translation_field else [0.0, 0.0, 0.0]
initial_rotation = list(rotation_field.getSFRotation()) if rotation_field else [0.0, 1.0, 0.0, 0.0]

print(f"[{robot_name}] >>> Starting NhanUI Controller...", flush=True)

# ==========================================
# CONSTANTS
# ==========================================
DEG_TO_RAD = 0.0174533
RAD_TO_DEG = 1 / DEG_TO_RAD

MIMIC_JOINTS = {
    "arm2_joint": ("arm1_joint", 1.0, 0),
    "gripper1_joint": ("arm1_joint", -1.0, 0),
    "gripper_2r_joint": ("gripper_2l_joint", -1.0, 0),
    "gripper_4l_joint": ("gripper_2l_joint", 1.0, 0),
    "gripper_4r_joint": ("gripper_2r_joint", 1.0, 0),
    "gripper_3r_joint": ("gripper_2r_joint", -1.0, 0),
    "gripper_3l_joint": ("gripper_3r_joint", -1.0, 0),
}

# Joint names for position sensor reporting
SENSOR_JOINTS = [
    "front_left_wheel_joint", "front_right_wheel_joint",
    "rear_left_wheel_joint", "rear_right_wheel_joint",
    "arm1_joint", "gripper_2l_joint"
]

# Motor names for motor target reporting
MOTOR_JOINTS = [
    "front_left_wheel_joint", "front_right_wheel_joint",
    "rear_left_wheel_joint", "rear_right_wheel_joint",
    "arm1_joint", "arm2_joint", "gripper1_joint",
    "gripper_2l_joint", "gripper_2r_joint"
]

# ==========================================
# 1. SENSORS (Position Sensors)
# ==========================================
position_sensors = {}
for jname in SENSOR_JOINTS:
    sensor_name = jname + "_sensor"
    try:
        sensor = robot.getDevice(sensor_name)
        if sensor:
            sensor.enable(timeStep)
            position_sensors[jname] = sensor
    except:
        pass

print(f"[{robot_name}] Position sensors enabled: {list(position_sensors.keys())}")

# ==========================================
# 2. MOTORS
# ==========================================
w_fl = robot.getDevice("front_left_wheel_joint")
w_fr = robot.getDevice("front_right_wheel_joint")
w_bl = robot.getDevice("rear_left_wheel_joint")
w_br = robot.getDevice("rear_right_wheel_joint")

left_motors = [w_fl, w_bl]
right_motors = [w_fr, w_br]
all_wheel_motors = [w_fl, w_fr, w_bl, w_br]

arm1_motor = robot.getDevice("arm1_joint")
arm2_motor = robot.getDevice("arm2_joint")
gripper1_motor = robot.getDevice("gripper1_joint")
gripper_2l_motor = robot.getDevice("gripper_2l_joint")
gripper_2r_motor = robot.getDevice("gripper_2r_joint")
gripper_4l_motor = robot.getDevice("gripper_4l_joint")
gripper_4r_motor = robot.getDevice("gripper_4r_joint")
gripper_3l_motor = robot.getDevice("gripper_3l_joint")
gripper_3r_motor = robot.getDevice("gripper_3r_joint")

all_motors = {
    "arm1_joint": arm1_motor,
    "arm2_joint": arm2_motor,
    "gripper1_joint": gripper1_motor,
    "gripper_2l_joint": gripper_2l_motor,
    "gripper_2r_joint": gripper_2r_motor,
    "gripper_4l_joint": gripper_4l_motor,
    "gripper_4r_joint": gripper_4r_motor,
    "gripper_3l_joint": gripper_3l_motor,
    "gripper_3r_joint": gripper_3r_motor,
}

# Also include wheel motors in the dict for target reporting
all_motors_extended = dict(all_motors)
all_motors_extended["front_left_wheel_joint"] = w_fl
all_motors_extended["front_right_wheel_joint"] = w_fr
all_motors_extended["rear_left_wheel_joint"] = w_bl
all_motors_extended["rear_right_wheel_joint"] = w_br

def _sync_mimic_joints(master_name, target_rad):
    for slave_name, (master, multiplier, offset) in MIMIC_JOINTS.items():
        if master == master_name and slave_name in all_motors and all_motors[slave_name]:
            slave_target = target_rad * multiplier + offset
            all_motors[slave_name].setPosition(slave_target)
    for slave_name, (master, multiplier, offset) in MIMIC_JOINTS.items():
        if master == master_name:
            slave_target = target_rad * multiplier + offset
            _sync_mimic_joints(slave_name, slave_target)

# ==========================================
# 3. CAMERA SETUP
# ==========================================
cameras = {}
camera_frame_skip = 5
camera_step_counter = 0
camera_jpeg_quality = 60

# Try to find cameras
CAMERA_NAMES_TO_TRY = ["camera", "Camera", "cam", "front_camera", "kinect_color"]
for cam_name in CAMERA_NAMES_TO_TRY:
    try:
        cam = robot.getDevice(cam_name)
        if cam:
            cam.enable(timeStep)
            cameras[cam_name] = cam
            print(f"[{robot_name}] Camera '{cam_name}' enabled: {cam.getWidth()}x{cam.getHeight()}")
    except:
        pass

def get_camera_base64(cam):
    """Get camera image as base64 JPEG string."""
    try:
        image = cam.getImage()
        if not image:
            return None
        w = cam.getWidth()
        h = cam.getHeight()

        # Try PIL first (best quality)
        try:
            from PIL import Image
            import io
            # Webots getImage() returns BGRA byte order
            img = Image.frombytes('RGBA', (w, h), image)
            # Swap R and B channels: BGRA was read as RGBA, so R=B, B=R
            r, g, b, a = img.split()
            img = Image.merge('RGB', (b, g, r))
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=camera_jpeg_quality)
            return base64.b64encode(buffer.getvalue()).decode('ascii')
        except ImportError:
            pass

        # Try OpenCV
        try:
            import numpy as np
            import cv2
            arr = np.frombuffer(image, dtype=np.uint8).reshape((h, w, 4))
            bgr = cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR)
            _, jpeg = cv2.imencode('.jpg', bgr, [cv2.IMWRITE_JPEG_QUALITY, camera_jpeg_quality])
            return base64.b64encode(jpeg.tobytes()).decode('ascii')
        except ImportError:
            pass

        # Fallback: raw RGBA → simple BMP-like (not ideal but works)
        return None
    except Exception as e:
        return None

# Send camera info at startup
if cameras:
    cam_info = {}
    for cam_name, cam in cameras.items():
        cam_info[cam_name] = {"width": cam.getWidth(), "height": cam.getHeight()}
    # Will be sent after STATUS:READY


# ==========================================
# 4. DRIVE API
# ==========================================
class DriveAPI:
    def __init__(self, wb_robot):
        self.robot = wb_robot
        self.max_velocity = 10.0
        for m in all_wheel_motors:
            if m:
                m.setPosition(float('inf'))
                m.setVelocity(0.0)
                self.max_velocity = m.getMaxVelocity()

        arm_motors_list = [arm1_motor, arm2_motor, gripper1_motor]
        for m in arm_motors_list:
            if m: m.setVelocity(0.5)

        gripper_motors_list = [gripper_2l_motor, gripper_2r_motor,
                               gripper_4l_motor, gripper_4r_motor,
                               gripper_3l_motor, gripper_3r_motor]
        for m in gripper_motors_list:
            if m: m.setVelocity(0.5)

    @staticmethod
    def _clamp_percent(speed):
        try: v = float(speed)
        except Exception: v = 0.0
        return max(0.0, min(100.0, v))

    def _set_wheels_percent(self, left_percent, right_percent):
        left_vel = (left_percent / 100.0) * self.max_velocity
        right_vel = (right_percent / 100.0) * self.max_velocity
        for m in left_motors:
            if m: m.setVelocity(left_vel)
        for m in right_motors:
            if m: m.setVelocity(-right_vel)

    def stop(self):
        self._set_wheels_percent(0.0, 0.0)
        if hw_bridge: hw_bridge.send("stop")

    def go_forward(self, speed):
        s = self._clamp_percent(speed)
        self._set_wheels_percent(s, s)
        if hw_bridge: hw_bridge.send("go_forward", speed=s)

    def go_backward(self, speed):
        s = self._clamp_percent(speed)
        self._set_wheels_percent(-s, -s)
        if hw_bridge: hw_bridge.send("go_backward", speed=s)

    def turn_left(self, speed):
        s = self._clamp_percent(speed)
        self._set_wheels_percent(-s, s)
        if hw_bridge: hw_bridge.send("turn_left", speed=s)

    def turn_right(self, speed):
        s = self._clamp_percent(speed)
        self._set_wheels_percent(s, -s)
        if hw_bridge: hw_bridge.send("turn_right", speed=s)

    def delay(self, seconds):
        try: target = float(seconds)
        except Exception: target = 0.0
        if target <= 0.0: return
        start_delay_timer = robot.getTime()
        while my_step() != -1:
            send_status()
            check_interrupt()
            if robot.getTime() - start_delay_timer >= target:
                break

    def arm_up(self, angle_degrees=0):
        if arm1_motor:
            target_rad = float(angle_degrees) * DEG_TO_RAD
            arm1_motor.setPosition(target_rad)
            _sync_mimic_joints("arm1_joint", target_rad)
        if hw_bridge: hw_bridge.send("arm_up", angle=float(angle_degrees))

    def arm_down(self, angle_degrees=45):
        if arm1_motor:
            target_rad = float(angle_degrees) * DEG_TO_RAD
            arm1_motor.setPosition(target_rad)
            _sync_mimic_joints("arm1_joint", target_rad)
        if hw_bridge: hw_bridge.send("arm_down", angle=float(angle_degrees))

    def close_gripper(self, angle_degrees=30):
        if gripper_2l_motor:
            target_rad = float(angle_degrees) * DEG_TO_RAD
            gripper_2l_motor.setPosition(target_rad)
            _sync_mimic_joints("gripper_2l_joint", target_rad)
        if hw_bridge: hw_bridge.send("close_gripper", angle=float(angle_degrees))

    def open_gripper(self, angle_degrees=-10):
        if gripper_2l_motor:
            target_rad = float(angle_degrees) * DEG_TO_RAD
            gripper_2l_motor.setPosition(target_rad)
            _sync_mimic_joints("gripper_2l_joint", target_rad)
        if hw_bridge: hw_bridge.send("open_gripper", angle=float(angle_degrees))

drive = DriveAPI(robot)

def wipe_motors():
    drive.stop()

# ==========================================
# 5. STATE MACHINE
# ==========================================
is_playing = True
imported_code = ""
is_code_executed = False
current_state = "IDLE"
manual_speed = 50
WWI_PAUSE_POLL_INTERVAL = 0.02

def my_step():
    r = robot.step(timeStep if is_playing else 0)
    if not is_playing:
        time.sleep(WWI_PAUSE_POLL_INTERVAL)
    return r

def do_reset_logic():
    global is_playing, is_code_executed, imported_code, current_state
    is_code_executed = False
    imported_code = ""
    current_state = "IDLE"
    __legacy_reset_drive_state()
    wipe_motors()
    if translation_field: translation_field.setSFVec3f(initial_translation)
    if rotation_field: rotation_field.setSFRotation(initial_rotation)
    if robot_node: robot_node.resetPhysics()
    robot.simulationSetMode(Supervisor.SIMULATION_MODE_REAL_TIME)
    is_playing = True
    robot.step(timeStep)

def apply_wwi_message(msg):
    global is_playing, imported_code, is_code_executed, current_state, manual_speed
    global camera_frame_skip, camera_jpeg_quality

    if msg.startswith("CODE:"):
        imported_code = msg[5:]
        is_code_executed = False
        current_state = "RUNNING"
        __legacy_reset_drive_state()
        wipe_motors()
        return "CODE"
    if msg == "CMD:PLAY":
        is_playing = True
        robot.simulationSetMode(Supervisor.SIMULATION_MODE_REAL_TIME)
        return None
    if msg == "CMD:PAUSE":
        is_playing = False
        robot.simulationSetMode(Supervisor.SIMULATION_MODE_PAUSE)
        return None
    if msg == "CMD:RESET":
        do_reset_logic()
        return "RESET"

    # Manual controls from NhanUI dashboard
    if msg == "CMD:HOME":
        drive.arm_up(0)
        drive.open_gripper(-10)
        drive.stop()
        current_state = "IDLE"
        return None
    if msg == "CMD:OPEN_GRIPPER":
        drive.open_gripper(-10)
        return None
    if msg == "CMD:CLOSE_GRIPPER":
        drive.close_gripper(30)
        return None
    if msg == "CMD:ARM_UP":
        drive.arm_up(0)
        return None
    if msg == "CMD:ARM_DOWN":
        drive.arm_down(45)
        return None
    if msg.startswith("CMD:ARM_TO:"):
        try:
            angle = float(msg[11:])
            drive.arm_up(angle)
        except: pass
        return None
    if msg == "CMD:FORWARD":
        drive.go_forward(manual_speed)
        return None
    if msg == "CMD:BACKWARD":
        drive.go_backward(manual_speed)
        return None
    if msg == "CMD:LEFT":
        drive.turn_left(manual_speed)
        return None
    if msg == "CMD:RIGHT":
        drive.turn_right(manual_speed)
        return None
    if msg == "CMD:STOP":
        drive.stop()
        return None
    if msg.startswith("SPEED:"):
        try: manual_speed = max(1, min(100, int(msg[6:])))
        except: pass
        return None

    # Camera settings
    if msg.startswith("CAMERA_SETTINGS:"):
        try:
            settings = json.loads(msg[16:])
            camera_frame_skip = settings.get("frameSkip", 5)
            camera_jpeg_quality = settings.get("quality", 60)
        except: pass
        return None

    # Sim-to-Real bridge control
    if msg == "SIM2REAL:ON":
        if hw_bridge:
            hw_bridge.enabled = True
            print(f"[{robot_name}] Sim-to-Real bridge ENABLED")
        return None
    if msg == "SIM2REAL:OFF":
        if hw_bridge:
            hw_bridge.enabled = False
            print(f"[{robot_name}] Sim-to-Real bridge DISABLED")
        return None
    if msg == "SIM2REAL:STATUS":
        if hw_bridge:
            status = hw_bridge.get_status()
            robot.wwiSendText("SIM2REAL:" + json.dumps(status))
        else:
            robot.wwiSendText("SIM2REAL:" + json.dumps({"enabled": False, "bridge_connected": False, "hardware_connected": False}))
        return None

    return None

def drain_wwi_queue(raise_for_interrupts=False):
    got_code = False
    got_reset = False
    while True:
        msg = robot.wwiReceiveText()
        if not msg: break
        kind = apply_wwi_message(msg)
        if kind == "CODE":
            got_code = True
            if raise_for_interrupts: raise Exception("NEW_CODE")
        elif kind == "RESET":
            got_reset = True
            if raise_for_interrupts: raise Exception("RESET")
    return got_code, got_reset

def check_interrupt():
    drain_wwi_queue(raise_for_interrupts=True)
    while not is_playing:
        if robot.step(0) == -1: break
        time.sleep(WWI_PAUSE_POLL_INTERVAL)
        drain_wwi_queue(raise_for_interrupts=True)

# ==========================================
# 6. STATUS REPORTING
# ==========================================
def get_joint_positions():
    positions = {}
    for jname, sensor in position_sensors.items():
        try:
            val = sensor.getValue()
            positions[jname] = round(val, 4)
        except:
            positions[jname] = 0.0
    return positions

def get_motor_targets():
    targets = {}
    for mname in MOTOR_JOINTS:
        motor = all_motors_extended.get(mname)
        if motor:
            try:
                target = motor.getTargetPosition()
                if target == float('inf') or target == float('-inf'):
                    # Wheels in velocity mode — report velocity instead
                    targets[mname] = round(motor.getVelocity(), 4)
                else:
                    targets[mname] = round(target, 4)
            except:
                targets[mname] = 0.0
    return targets

def send_status():
    global camera_step_counter

    joint_positions = get_joint_positions()
    motor_targets = get_motor_targets()
    distance_val = front_sensor.read()

    status = {
        "time": round(robot.getTime(), 2),
        "state": current_state,
        "distance": round(distance_val, 1),
        "joints": joint_positions,
        "motors": motor_targets
    }
    robot.wwiSendText("STATUS:" + json.dumps(status))

    # Camera frames
    if cameras:
        camera_step_counter += 1
        if camera_step_counter >= camera_frame_skip:
            camera_step_counter = 0
            for cam_name, cam in cameras.items():
                camera_data = get_camera_base64(cam)
                if camera_data:
                    robot.wwiSendText(f"CAMERA:{cam_name}:{camera_data}")


# ==========================================
# 7. ROBOT PROXY
# ==========================================
legacy_motor_bindings = {}
legacy_left_percent = 0.0
legacy_right_percent = 0.0

def _guess_motor_side(tag: str):
    t = (tag or '').strip().lower()
    if ('left' in t) or ('_fl' in t) or ('_bl' in t): return 'left'
    if ('right' in t) or ('_fr' in t) or ('_br' in t): return 'right'
    return None

def __legacy_bind_motor(var_name, motor_name):
    side = _guess_motor_side(motor_name) or _guess_motor_side(var_name)
    legacy_motor_bindings[str(var_name)] = side

def __legacy_reset_drive_state():
    global legacy_left_percent, legacy_right_percent
    legacy_left_percent = 0.0
    legacy_right_percent = 0.0
    drive._set_wheels_percent(0.0, 0.0)

def __legacy_set_motor_speed(var_name, speed):
    global legacy_left_percent, legacy_right_percent
    try: s = float(speed)
    except Exception: s = 0.0
    s = max(-100.0, min(100.0, s))
    key = str(var_name)
    side = legacy_motor_bindings.get(key)
    if side is None: side = _guess_motor_side(key)
    if side == 'left': legacy_left_percent = s
    elif side == 'right': legacy_right_percent = s
    else:
        legacy_left_percent = s
        legacy_right_percent = s
    drive._set_wheels_percent(legacy_left_percent, legacy_right_percent)

class RobotProxy:
    def __getattr__(self, name): return getattr(robot, name)
    def step(self, ts):
        r = robot.step(timeStep if is_playing else 0)
        if not is_playing: time.sleep(WWI_PAUSE_POLL_INTERVAL)
        return r
    def go_forward(self, speed): drive.go_forward(speed)
    def go_backward(self, speed): drive.go_backward(speed)
    def turn_left(self, speed): drive.turn_left(speed)
    def turn_right(self, speed): drive.turn_right(speed)
    def arm_up(self, angle=0): drive.arm_up(angle)
    def arm_down(self, angle=45): drive.arm_down(angle)
    def close_gripper(self, angle=30): drive.close_gripper(angle)
    def open_gripper(self, angle=-10): drive.open_gripper(angle)

myRobot = RobotProxy()

robot.go_forward = myRobot.go_forward
robot.go_backward = myRobot.go_backward
robot.turn_left = myRobot.turn_left
robot.turn_right = myRobot.turn_right
robot.arm_up = myRobot.arm_up
robot.arm_down = myRobot.arm_down
robot.close_gripper = myRobot.close_gripper
robot.open_gripper = myRobot.open_gripper

def delay(seconds): drive.delay(seconds)
def stop_all():
    drive._set_wheels_percent(0.0, 0.0)
    if hw_bridge: hw_bridge.send("stop")
    raise Exception("STOP_ALL")
def while_tick():
    check_interrupt()
    if robot.step(timeStep) == -1: raise Exception("STOP_ALL")

# --- DISTANCE SENSOR ---
class Ultrasonic:
    def __init__(self): self.sensor = None
    def begin(self, name: str, step: int):
        self.sensor = robot.getDevice(name)
        if self.sensor: self.sensor.enable(step)
    def read(self) -> float:
        if self.sensor is None: return 99999.0
        return self.sensor.getValue()

front_sensor = Ultrasonic()
front_sensor.begin("distance sensor", timeStep)
def getDistance(): return front_sensor.read()

# ==========================================
# 8. MAIN LOOP
# ==========================================
robot.simulationSetMode(Supervisor.SIMULATION_MODE_REAL_TIME)
robot.wwiSendText("STATUS:READY")

# Send camera info
if cameras:
    cam_info = {}
    for cam_name, cam in cameras.items():
        cam_info[cam_name] = {"width": cam.getWidth(), "height": cam.getHeight()}
    robot.wwiSendText("CAMERAS:" + json.dumps(cam_info))

print(f"[{robot_name}] >>> Backend Ready! Motors: wheels={bool(w_fl)}, arm={bool(arm1_motor)}, gripper={bool(gripper_2l_motor)}, cameras={list(cameras.keys())}")

while True:
    if my_step() == -1: break

    # Send rich status every step
    send_status()

    got_code_this_step, got_reset_this_step = drain_wwi_queue(raise_for_interrupts=False)

    if got_code_this_step:
        is_playing = True
        robot.simulationSetMode(Supervisor.SIMULATION_MODE_REAL_TIME)
        current_state = "RUNNING"
        print(f"[{robot_name}] >>> Code loaded — running.")
    if got_reset_this_step:
        print(f"[{robot_name}] >>> Robot reset.")

    if is_playing and imported_code and not is_code_executed:
        is_code_executed = True
        try:
            exec(imported_code, globals())
            imported_code = ""
            current_state = "IDLE"
        except Exception as e:
            if str(e) not in ["NEW_CODE", "RESET", "STOP_ALL"]:
                print(f"[{robot_name}] ERROR: {e}", file=sys.stderr)
                robot.wwiSendText("ERROR:" + str(e))
            if str(e) != "RESET":
                is_playing = False
                current_state = "IDLE"
