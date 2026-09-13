from controller import Robot, Motor

MAX_PWM = 100
MAX_SPEED = 10.0
TIME_STEP = 64
DISTANCE_NOT_AVAILABLE = 99999.0


class SumoRobot:
    """API điều khiển robot sumo theo hướng đối tượng."""

    def __init__(self, time_step: int = TIME_STEP):
        self.time_step = time_step
        self.robot = Robot()

        # Gắn 4 động cơ đúng theo tên trong mô hình Webots
        self.wheel_fl: Motor = self.robot.getDevice("Wheel_FL")
        self.wheel_fr: Motor = self.robot.getDevice("Wheel_FR")
        self.wheel_bl: Motor = self.robot.getDevice("Wheel_BL")
        self.wheel_br: Motor = self.robot.getDevice("Wheel_BR")

        self._motors = [
            self.wheel_fl,
            self.wheel_fr,
            self.wheel_bl,
            self.wheel_br,
        ]

        for motor in self._motors:
            motor.setPosition(float("inf"))
            motor.setVelocity(0.0)

        self.ultrasonic = self._init_ultrasonic("distance sensor")

    def _init_ultrasonic(self, sensor_name: str):
        try:
            sensor = self.robot.getDevice(sensor_name)
        except Exception:
            sensor = None

        if sensor is None:
            print(f"Cảnh báo: không tìm thấy cảm biến '{sensor_name}'.")
            return None

        if not hasattr(sensor, "enable") or not hasattr(sensor, "getValue"):
            print(f"Cảnh báo: thiết bị '{sensor_name}' không phải cảm biến khoảng cách.")
            return None

        sensor.enable(self.time_step)
        return sensor

    def _clamp_pwm(self, pwm: float) -> float:
        if pwm > MAX_PWM:
            return float(MAX_PWM)
        if pwm < -MAX_PWM:
            return float(-MAX_PWM)
        return float(pwm)

    def _to_velocity(self, pwm: float) -> float:
        pwm = self._clamp_pwm(pwm)
        return (pwm / MAX_PWM) * MAX_SPEED

    def _set_side_velocity(self, left_pwm: float, right_pwm: float) -> None:
        left_velocity = self._to_velocity(left_pwm)
        right_velocity = self._to_velocity(right_pwm)

        # Bên trái: trước trái + sau trái
        self.wheel_fl.setVelocity(left_velocity)
        self.wheel_bl.setVelocity(left_velocity)

        # Bên phải: trước phải + sau phải
        self.wheel_fr.setVelocity(right_velocity)
        self.wheel_br.setVelocity(right_velocity)

    def _run_for(self, duration_s: float) -> None:
        total_ms = int(max(0.0, duration_s) * 1000)
        elapsed_ms = 0

        while elapsed_ms < total_ms and self.robot.step(self.time_step) != -1:
            elapsed_ms += self.time_step

    def move(self, left_pwm: float, right_pwm: float) -> None:
        self._set_side_velocity(left_pwm, right_pwm)

    def delay(self, duration_s: float) -> None:
        self._run_for(duration_s)

    def go_forward(self, speed: float) -> None:
        speed = abs(speed)
        self.move(speed, speed)

    def go_backward(self, speed: float) -> None:
        speed = abs(speed)
        self.move(-speed, -speed)

    def turn_left(self, speed: float) -> None:
        speed = abs(speed)
        self.move(-speed, speed)

    def turn_right(self, speed: float) -> None:
        speed = abs(speed)
        self.move(speed, -speed)

    def read_distance(self) -> float:
        if self.ultrasonic is None:
            return DISTANCE_NOT_AVAILABLE
        return self.ultrasonic.getValue()

    def print_distance(self, distance: float) -> None:
        print("Khoảng cách:", round(distance), "mm")

    def is_target_detected(self, distance: float, threshold_mm: float = 2000) -> bool:
        return distance < threshold_mm

    def execute_attack_sequence(
        self,
        stop_duration: float = 0.5,
        attack_speed: float = 50,
        attack_duration: float = 10,
        retreat_speed: float = 50,
        retreat_duration: float = 10,
    ) -> None:
        self.go_forward(0)
        self.delay(stop_duration)
        self.go_forward(attack_speed)
        self.delay(attack_duration)
        self.go_backward(retreat_speed)
        self.delay(retreat_duration)
