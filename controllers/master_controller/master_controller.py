from controller import Supervisor
import sys
import time

robot = Supervisor()
timeStep = int(robot.getBasicTimeStep())
robot_node = robot.getSelf()
robot_name = robot.getName() # TỰ ĐỘNG LẤY TÊN ROBOT (robot1, robot2...)

# Lưu tọa độ ban đầu để Reset xe không làm giật sa bàn
translation_field = robot_node.getField("translation") if robot_node else None
rotation_field = robot_node.getField("rotation") if robot_node else None
initial_translation = list(translation_field.getSFVec3f()) if translation_field else [0.0, 0.0, 0.0]
initial_rotation = list(rotation_field.getSFRotation()) if rotation_field else [0.0, 1.0, 0.0, 0.0]

print(f"[{robot_name}] >>> Đang khởi động Lõi Điều Khiển...", flush=True)

# ==========================================
# 1. DRIVE API (HỆ THỐNG TRUYỀN ĐỘNG)
# ==========================================
w_fl = robot.getDevice("Wheel_FL")
w_fr = robot.getDevice("Wheel_FR")
w_bl = robot.getDevice("Wheel_BL")
w_br = robot.getDevice("Wheel_BR")
left_motors = [w_fl, w_bl]
right_motors = [w_fr, w_br]
all_motors = [w_fl, w_fr, w_bl, w_br]

class DriveAPI:
    def __init__(self, wb_robot):
        self.robot = wb_robot
        self.max_velocity = 0.0
        for m in all_motors:
            if m:
                m.setPosition(float('inf'))
                m.setVelocity(0.0)
                if self.max_velocity == 0.0:
                    self.max_velocity = m.getMaxVelocity()

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
            if m: m.setVelocity(right_vel)

    def stop(self):
        self._set_wheels_percent(0.0, 0.0)

    def go_forward(self, speed):
        s = self._clamp_percent(speed)
        self._set_wheels_percent(s, s)

    def go_backward(self, speed):
        s = self._clamp_percent(speed)
        self._set_wheels_percent(-s, -s)

    def turn_left(self, speed):
        s = self._clamp_percent(speed)
        self._set_wheels_percent(-s, s)

    def turn_right(self, speed):
        s = self._clamp_percent(speed)
        self._set_wheels_percent(s, -s)

    def delay(self, seconds):
        try: target = float(seconds)
        except Exception: target = 0.0
        if target <= 0.0: return

        start_delay_timer = robot.getTime()
        while my_step() != -1:
            robot.wwiSendText("TIME:" + str(robot.getTime()))
            check_interrupt()
            if robot.getTime() - start_delay_timer >= target:
                break

drive = DriveAPI(robot)

def wipe_motors():
    drive.stop()

# ==========================================
# 2. STATE MACHINE (KHÓA TRẠNG THÁI & RESET MỀM)
# ==========================================
is_playing = True
imported_code = ""
is_code_executed = False
WWI_PAUSE_POLL_INTERVAL = 0.02

def my_step():
    r = robot.step(timeStep if is_playing else 0)
    if not is_playing:
        time.sleep(WWI_PAUSE_POLL_INTERVAL)
    return r

def do_reset_logic():
    global is_playing, is_code_executed, imported_code
    is_code_executed = False
    imported_code = ""
    __legacy_reset_drive_state()
    wipe_motors()

    # Reset mềm: Đưa xe về vạch xuất phát mà không load lại Webots
    if translation_field: translation_field.setSFVec3f(initial_translation)
    if rotation_field: rotation_field.setSFRotation(initial_rotation)
    if robot_node: robot_node.resetPhysics()

    robot.simulationSetMode(Supervisor.SIMULATION_MODE_REAL_TIME)
    is_playing = True
    robot.step(timeStep)

def apply_wwi_message(msg):
    global is_playing, imported_code, is_code_executed
    if msg.startswith("CODE:"):
        imported_code = msg[5:]
        is_code_executed = False
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
# 3. NÃO TĨNH & LỚP ỦY QUYỀN (ROBOT PROXY)
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

myRobot = RobotProxy()
robot.go_forward = myRobot.go_forward
robot.go_backward = myRobot.go_backward
robot.turn_left = myRobot.turn_left
robot.turn_right = myRobot.turn_right

def delay(seconds): drive.delay(seconds)
def stop_all():
    drive._set_wheels_percent(0.0, 0.0)
    raise Exception("STOP_ALL")
def while_tick():
    check_interrupt()
    if robot.step(timeStep) == -1: raise Exception("STOP_ALL")

# --- CẢM BIẾN VẬT CẢN ---
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
def getLSColor(camImg): pass
def getLSGray(camImg): pass
def updateGyro(): pass
def getAngle(): return 0.0

# ==========================================
# 4. VÒNG LẶP CHÍNH (MAIN LOOP)
# ==========================================
robot.simulationSetMode(Supervisor.SIMULATION_MODE_REAL_TIME)
robot.wwiSendText("STATUS:READY")
print(f"[{robot_name}] >>> Backend Sẵn sàng! Đang mở kênh WebSockets...")

while True:
    if my_step() == -1: break
    robot.wwiSendText(f"TIME:{robot.getTime():.2f}")

    got_code_this_step, got_reset_this_step = drain_wwi_queue(raise_for_interrupts=False)

    if got_code_this_step:
        is_playing = True
        robot.simulationSetMode(Supervisor.SIMULATION_MODE_REAL_TIME)
        print(f"[{robot_name}] >>> Đã nạp Code — đang chạy.")
    if got_reset_this_step:
        print(f"[{robot_name}] >>> Đã Reset xe.")

    if is_playing and imported_code and not is_code_executed:
        is_code_executed = True
        try:
            exec(imported_code, globals())
            imported_code = ""
        except Exception as e:
            if str(e) not in ["NEW_CODE", "RESET", "STOP_ALL"]:
                print(f"[{robot_name}] ❌ LỖI TỪ WEBAPP: {e}", file=sys.stderr)
            if str(e) != "RESET":
                is_playing = False