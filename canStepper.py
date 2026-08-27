import can
import time
from motor import BaseMotorController

class MKSServo42DCANController(BaseMotorController):
    """
    CAN Bus driver for NEMA 17 with MKS Servo42D.
    Inherits step tracking and angle limits from BaseMotorController.
    """
    def __init__(self, channel='can0', bitrate=500000, motor_id=0x01, step_size=10, min_angle=0, max_angle=180, **kwargs):
        # 1. Initialize parent BaseMotorController attributes (self.angle, self.step_size, etc.)
        super().__init__(step_size=step_size, min_angle=min_angle, max_angle=max_angle, **kwargs)
        
        self.motor_id = motor_id
        self.channel = channel
        self.bitrate = bitrate
        
        # 2. Connect to SocketCAN interface (MKS CANable v2.0)
        try:
            self.bus = can.interface.Bus(
                channel=self.channel, 
                bustype='socketcan', 
                bitrate=self.bitrate
            )
            print(f"[CAN] Successfully connected to {self.channel}")
        except Exception as e:
            print(f"[CAN Error] Could not connect to {self.channel}: {e}")
            self.bus = None

        # 3. Automatically send mode initialization to motor on startup
        if self.bus:
            self._init_motor_mode()

    def _calculate_checksum(self, can_id: int, payload: list) -> int:
        """Calculate 8-bit checksum byte: (CAN_ID + sum(payload)) & 0xFF."""
        return (can_id + sum(payload)) & 0xFF

    def _send_cmd(self, can_id: int, data_bytes: list):
        """Assemble packet with checksum and send over CAN bus."""
        if not self.bus:
            print("[CAN Error] Bus not connected.")
            return

        chk = self._calculate_checksum(can_id, data_bytes)
        payload = data_bytes + [chk]

        msg = can.Message(
            arbitration_id=can_id,
            data=payload,
            is_extended_id=False
        )
        try:
            self.bus.send(msg)
        except can.CanError as e:
            print(f"[CAN Error] Failed to send frame: {e}")

    def _init_motor_mode(self):
        """Set working mode to Bus FOC Mode (0x82 0x05) on startup."""
        print(f"[CAN] Initializing motor 0x{self.motor_id:02X} to Bus FOC mode...")
        
        # Command: 0x82 (Set mode), 0x05 (Bus FOC Mode)
        # Broadcast setting (ID 0x00) -> CAN ID: 000, Data: [0x82, 0x05], Checksum: 0x87
        self._send_cmd(0x00, [0x82, 0x05])
        time.sleep(0.05)

        print(f"[CAN] Broadcast ebales multi-motor synchronous control function")
        self._send_cmd(0x00, [0x4A, 0x01])
        time.sleep(0.05)

    def set_angle(self, target_angle: int):
        # """Hardware implementation of the abstract set_angle method."""
        # # Clamp angle between min_angle and max_angle
        # target_angle = max(self.min_angle, min(self.max_angle, target_angle))
        # angle_diff = target_angle - self.angle
        
        # if angle_diff == 0:
        #     return

        # # Direction flag: 0x00 for Clockwise (right), 0x80 for Counter-Clockwise (left)
        # direction_flag = 0x00 if angle_diff > 0 else 0x80
        # speed_rpm = 64  # Speed parameter (~100 RPM in hex: 0x64)
        # accel = 0x02    # Acceleration parameter

        # # Convert degree difference into step pulses (assuming 3200 steps/rev)
        # pulses = int(abs(angle_diff) * (3200 / 360))
        
        # # Split 32-bit pulse integer into 4 byte array
        # p_bytes = [
        #     (pulses >> 24) & 0xFF,
        #     (pulses >> 16) & 0xFF,
        #     (pulses >> 8) & 0xFF,
        #     pulses & 0xFF
        # ]

        # # Command 0xFD: Relative Pulse Movement
        # cmd_payload = [0xFD, direction_flag | speed_rpm, accel] + p_bytes
        
        # self._send_cmd(self.motor_id, cmd_payload)
        # self.angle = target_angle
        # print(f"[CAN Motor] Moved to angle: {self.angle}° (Diff: {angle_diff}°)")

        self._send_cmd(0x01, [0xF6, 0x02, 0x80, 0x02])
        self._send_cmd(0x00, [0x4B])


    def close(self):
        """Close CAN bus connection."""
        if self.bus:
            self.bus.shutdown()