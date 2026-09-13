"""
Robot Controller Library for DienBien Robot
Supports mimic joints synchronization for parallel linkage mechanism.

This library automatically synchronizes mimic joints as defined in URDF:
- arm2_joint mimics arm1_joint (multiplier=1)
- gripper1_joint mimics arm1_joint (multiplier=-1) - keeps gripper horizontal
- gripper_2r_joint mimics gripper_2l_joint (multiplier=-1)
- gripper_4l_joint mimics gripper_2l_joint (multiplier=1)
- gripper_4r_joint mimics gripper_2r_joint (multiplier=1)
- gripper_3r_joint mimics gripper_2r_joint (multiplier=-1)
- gripper_3l_joint mimics gripper_3r_joint (multiplier=-1)
"""

from controller import Robot, Motor, PositionSensor

MAX_PWM = 100
MAX_SPEED = 10.0  # rad/s for wheels
TIME_STEP = 64
DISTANCE_NOT_AVAILABLE = 99999.0

# Unit conversion constants
RPM_TO_RAD_S = 0.10472
DEG_TO_RAD = 0.0174533
RAD_TO_DEG = 1 / DEG_TO_RAD

# Mimic joint definitions from URDF
# Format: {slave_joint: (master_joint, multiplier, offset)}
MIMIC_JOINTS = {
    "arm2_joint": ("arm1_joint", 1.0, 0),
    "gripper1_joint": ("arm1_joint", -1.0, 0),
    "gripper_2r_joint": ("gripper_2l_joint", -1.0, 0),
    "gripper_4l_joint": ("gripper_2l_joint", 1.0, 0),
    "gripper_4r_joint": ("gripper_2r_joint", 1.0, 0),
    "gripper_3r_joint": ("gripper_2r_joint", -1.0, 0),
    "gripper_3l_joint": ("gripper_3r_joint", -1.0, 0),
}

# All joint names in the robot
ALL_JOINTS = [
    # Wheels (controllable)
    "front_left_wheel_joint",
    "front_right_wheel_joint",
    "rear_left_wheel_joint",
    "rear_right_wheel_joint",
    # Arm (master)
    "arm1_joint",
    # Arm (mimic)
    "arm2_joint",
    # Gripper (master)
    "gripper_2l_joint",
    # Gripper (mimic)
    "gripper1_joint",
    "gripper_2r_joint",
    "gripper_4l_joint",
    "gripper_4r_joint",
    "gripper_3l_joint",
    "gripper_3r_joint",
]


class DienBienRobot:
    """API dieu khien robot DienBien voi 4 banh + canh tay song song + gripper.
    
    Parallel linkage mechanism with automatic mimic joint synchronization:
    - arm1_joint: Main arm motor (master)
    - arm2_joint: Parallel bar (auto-synced with arm1)
    - gripper1_joint: Keeps gripper horizontal (auto-synced with arm1, multiplier=-1)
    - gripper_2l_joint: Main gripper motor (master for gripper fingers)
    """

    def __init__(self, time_step: int = TIME_STEP):
        """Initialize robot controller with mimic joint support."""
        self.time_step = time_step
        self.robot = Robot()
        
        # Dictionary to store all motors
        self.motors = {}
        self.sensors = {}
        
        # Initialize all joints
        for joint_name in ALL_JOINTS:
            motor = self._try_get_device(joint_name)
            if motor:
                self.motors[joint_name] = motor
                motor.setVelocity(1.0)  # Default velocity
                
            sensor = self._try_get_device(joint_name + "_sensor")
            if sensor:
                self.sensors[joint_name] = sensor
                sensor.enable(self.time_step)
        
        print(f"Initialized {len(self.motors)} motors, {len(self.sensors)} sensors")
        print(f"Motors: {list(self.motors.keys())}")
        
        # Setup wheel motors for velocity control
        wheel_joints = [
            "front_left_wheel_joint",
            "front_right_wheel_joint",
            "rear_left_wheel_joint",
            "rear_right_wheel_joint",
        ]
        for name in wheel_joints:
            if name in self.motors:
                self.motors[name].setPosition(float("inf"))
                self.motors[name].setVelocity(0.0)
        
        # Convenience references
        self.arm1_motor = self.motors.get("arm1_joint")
        self.arm1_sensor = self.sensors.get("arm1_joint")
        self.gripper_motor = self.motors.get("gripper_2l_joint")
        self.gripper_sensor = self.sensors.get("gripper_2l_joint")
        
        # Ultrasonic sensor
        self.ultrasonic = self._init_ultrasonic("distance sensor")

    def _try_get_device(self, name: str):
        """Try to get a device, return None if not found."""
        if name is None:
            return None
        try:
            device = self.robot.getDevice(name)
            return device
        except:
            return None

    def _init_ultrasonic(self, sensor_name: str):
        try:
            sensor = self.robot.getDevice(sensor_name)
            if sensor and hasattr(sensor, "enable"):
                sensor.enable(self.time_step)
                return sensor
        except:
            pass
        return None

    def _sync_mimic_joints(self, master_name: str, target_rad: float):
        """Synchronize all mimic joints that follow the given master joint."""
        for slave_name, (master, multiplier, offset) in MIMIC_JOINTS.items():
            if master == master_name and slave_name in self.motors:
                slave_target = target_rad * multiplier + offset
                self.motors[slave_name].setPosition(slave_target)
        
        # Handle chain mimic (gripper_3l → gripper_3r → gripper_2r → gripper_2l)
        # This is called recursively
        for slave_name, (master, multiplier, offset) in MIMIC_JOINTS.items():
            if master == master_name:
                slave_target = target_rad * multiplier + offset
                self._sync_mimic_joints(slave_name, slave_target)

    def _clamp_pwm(self, pwm: float) -> float:
        if pwm > MAX_PWM:
            return float(MAX_PWM)
        if pwm < -MAX_PWM:
            return float(-MAX_PWM)
        return float(pwm)

    def _to_velocity(self, pwm: float) -> float:
        pwm = self._clamp_pwm(pwm)
        return (pwm / MAX_PWM) * MAX_SPEED

    def step(self) -> int:
        """Run one simulation step. Returns -1 if simulation ended."""
        return self.robot.step(self.time_step)

    def delay(self, duration_s: float) -> None:
        """Wait for specified duration in seconds."""
        total_ms = int(max(0.0, duration_s) * 1000)
        elapsed_ms = 0
        while elapsed_ms < total_ms and self.robot.step(self.time_step) != -1:
            elapsed_ms += self.time_step

    # ============== WHEEL CONTROL ==============

    def move(self, left_pwm: float, right_pwm: float) -> None:
        """Set left and right wheel speeds (PWM: -100 to 100)."""
        left_vel = self._to_velocity(left_pwm)
        right_vel = self._to_velocity(right_pwm)
        
        if "front_left_wheel_joint" in self.motors:
            self.motors["front_left_wheel_joint"].setVelocity(left_vel)
        if "rear_left_wheel_joint" in self.motors:
            self.motors["rear_left_wheel_joint"].setVelocity(left_vel)
        if "front_right_wheel_joint" in self.motors:
            self.motors["front_right_wheel_joint"].setVelocity(-right_vel)
        if "rear_right_wheel_joint" in self.motors:
            self.motors["rear_right_wheel_joint"].setVelocity(-right_vel)

    def go_forward(self, speed: float) -> None:
        self.move(abs(speed), abs(speed))

    def go_backward(self, speed: float) -> None:
        self.move(-abs(speed), -abs(speed))

    def turn_left(self, speed: float) -> None:
        self.move(-abs(speed), abs(speed))

    def turn_right(self, speed: float) -> None:
        self.move(abs(speed), -abs(speed))

    def stop_wheels(self) -> None:
        self.move(0, 0)

    # ============== ARM CONTROL (with mimic sync) ==============

    def has_arm(self) -> bool:
        return self.arm1_motor is not None

    def set_arm_velocity(self, velocity: float) -> None:
        """Set arm motor velocity in rad/s."""
        vel = abs(velocity)
        if self.arm1_motor:
            self.arm1_motor.setVelocity(vel)
        # Also set velocity for mimic joints
        if "arm2_joint" in self.motors:
            self.motors["arm2_joint"].setVelocity(vel)
        if "gripper1_joint" in self.motors:
            self.motors["gripper1_joint"].setVelocity(vel)

    def arm_up(self, angle_degrees: float = 0) -> None:
        """Move arm up. Auto-syncs arm2 and gripper1 to maintain parallel linkage."""
        self.arm_to_position(angle_degrees)

    def arm_down(self, angle_degrees: float = 45) -> None:
        """Move arm down. Auto-syncs arm2 and gripper1 to maintain parallel linkage."""
        self.arm_to_position(angle_degrees)

    def arm_to_position(self, angle_degrees: float) -> None:
        """Move arm to specific angle. Auto-syncs mimic joints."""
        if self.arm1_motor:
            target_rad = angle_degrees * DEG_TO_RAD
            self.arm1_motor.setPosition(target_rad)
            # Sync mimic joints
            self._sync_mimic_joints("arm1_joint", target_rad)

    def get_arm_position(self) -> float:
        """Get current arm position in degrees."""
        if self.arm1_sensor:
            return self.arm1_sensor.getValue() * RAD_TO_DEG
        return 0.0

    def wait_arm_done(self, tolerance_deg: float = 1.0) -> None:
        """Wait until arm reaches target position."""
        if not self.arm1_motor or not self.arm1_sensor:
            return
        tolerance_rad = tolerance_deg * DEG_TO_RAD
        target = self.arm1_motor.getTargetPosition()
        while self.robot.step(self.time_step) != -1:
            current = self.arm1_sensor.getValue()
            if abs(target - current) < tolerance_rad:
                break

    # ============== GRIPPER CONTROL (with mimic sync) ==============

    def has_gripper(self) -> bool:
        return self.gripper_motor is not None

    def set_gripper_velocity(self, velocity: float) -> None:
        """Set gripper motor velocity in rad/s."""
        vel = abs(velocity)
        # Set velocity for all gripper joints
        gripper_joints = ["gripper_2l_joint", "gripper_2r_joint", 
                         "gripper_4l_joint", "gripper_4r_joint",
                         "gripper_3l_joint", "gripper_3r_joint"]
        for name in gripper_joints:
            if name in self.motors:
                self.motors[name].setVelocity(vel)

    def open_gripper(self, angle_degrees: float = 0) -> None:
        """Open gripper. Auto-syncs all gripper fingers."""
        self.gripper_to_position(angle_degrees)

    def close_gripper(self, angle_degrees: float = 45) -> None:
        """Close gripper. Auto-syncs all gripper fingers."""
        self.gripper_to_position(angle_degrees)

    def gripper_to_position(self, angle_degrees: float) -> None:
        """Move gripper to specific angle. Auto-syncs mimic joints."""
        if self.gripper_motor:
            target_rad = angle_degrees * DEG_TO_RAD
            self.gripper_motor.setPosition(target_rad)
            # Sync mimic joints
            self._sync_mimic_joints("gripper_2l_joint", target_rad)

    def get_gripper_position(self) -> float:
        """Get current gripper position in degrees."""
        if self.gripper_sensor:
            return self.gripper_sensor.getValue() * RAD_TO_DEG
        return 0.0

    def wait_gripper_done(self, tolerance_deg: float = 1.0) -> None:
        """Wait until gripper reaches target position."""
        if not self.gripper_motor or not self.gripper_sensor:
            return
        tolerance_rad = tolerance_deg * DEG_TO_RAD
        target = self.gripper_motor.getTargetPosition()
        while self.robot.step(self.time_step) != -1:
            current = self.gripper_sensor.getValue()
            if abs(target - current) < tolerance_rad:
                break

    # ============== SENSOR CONTROL ==============

    def read_distance(self) -> float:
        if self.ultrasonic is None:
            return DISTANCE_NOT_AVAILABLE
        return self.ultrasonic.getValue()


# Backward compatibility
SumoRobot = DienBienRobot
