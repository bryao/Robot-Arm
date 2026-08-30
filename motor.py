import abc

class BaseMotorController(abc.ABC):
    def __init__(self, step_size=10, min_angle=0, max_angle=180):
        self.angle = 90  # Start at center (90°)
        self.step_size = step_size
        self.min_angle = min_angle
        self.max_angle = max_angle

    def turn_left(self):
        self.set_angle(self.angle - self.step_size)
    #     self.turn_left()

    def turn_right(self):
        self.set_angle(self.angle + self.step_size)
    #     self.turn_right()

    @abc.abstractmethod
    def set_angle(self, angle: int):
        """Hardware implementation to move motor to target angle."""
        pass

    def return_home(self):
        """Hardware implementation to move motor to target back to home position"""
        pass

class MockMotorController(BaseMotorController):
    """Simulated motor driver for testing on PC without hardware attached."""
    def set_angle(self, angle: int):
        self.angle = max(self.min_angle, min(self.max_angle, angle))
        print(f"[MockMotor] Camera rotated to position: {self.angle}°")