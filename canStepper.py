import can
import time
from motor import BaseMotorController

class MKSServo42DCANController(BaseMotorController):
    """
    CAN Bus driver for NEMA 17 with MKS Servo42D.
    Inherits step tracking and angle limits from BaseMotorController.
    """
    def __init__(self, channel='can0', bitrate=500000,gear_ratio=50.0, motor_id=0x01, step_size=10, min_angle=0, max_angle=180, **kwargs):
        # 1. Initialize parent BaseMotorController attributes (self.angle, self.step_size, etc.)
        super().__init__(step_size=step_size, min_angle=min_angle, max_angle=max_angle, **kwargs)
        
        self.motor_id = motor_id
        self.channel = channel
        self.bitrate = bitrate
        self.gear_ratio = gear_ratio  # 1:50 Gearbox multiplier
        
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
        self._send_cmd(0x01, [0x82, 0x05])
        time.sleep(0.05)

        # self._send_cmd(0x01, [0xF3, 0x01])
        # time.sleep(0.05)

        # print(f"[CAN] Broadcast ebales multi-motor synchronous control function")
        # self._send_cmd(0x00, [0x4A, 0x01])
        # time.sleep(0.05)

    # def turn_left(self):
    #     self._send_cmd(0x01, [0xF4, 0x01, 0x2C, 0x02, 0xFD, 0x80, 0x00])
    #     # self._send_cmd(0x01, [0xF4, 0x01])
    #     # self._send_cmd(0x01, [0x4B])

    # def turn_right(self):
    #     self._send_cmd(0x01, [0xF4, 0x01, 0x2C, 0x02, 0x02, 0x80, 0x00])
    #     # self._send_cmd(0x01, [0x4B])

    def set_angle(self, target_angle: int):
        target_angle = max(self.min_angle, min(self.max_angle, target_angle))
        angle_diff = target_angle - self.angle

        print(f"target angle:{target_angle}")
        
        if angle_diff == 0:
            return

        # 1. Direction Bit (b7 of Byte 2): 0x80 if negative, 0x00 if positive
        dir_bit = 0x80 if angle_diff > 0 else 0x00

        # 2. Speed (12-bit value: 0 to 3000 RPM)
        # Example: 320 RPM -> Hex 0x140 (Byte2 speed portion = 0x1, Byte3 = 0x40)
        speed_rpm = 320  
        speed_high = (speed_rpm >> 8) & 0x0F  # Bits 11-8 -> fits in b3-b0
        speed_low = speed_rpm & 0xFF          # Bits 7-0  -> Byte 3

        # Combine Direction bit (b7) and High Speed bits (b3-b0) for Byte 2
        byte2 = dir_bit | speed_high
        byte3 = speed_low
        byte4_acc = 0x02  # Acceleration (0-255)

        # 3. Pulses (3-byte field / Bytes 5-7: 0 to 0xFFFFFF)
        motor_degrees = abs(angle_diff) * self.gear_ratio
        pulses = int(motor_degrees * (3200 / 360))  # Assuming 16 microsteps (3200 PPR)

        relpulses_bytes = [
            (pulses >> 16) & 0xFF,
            (pulses >> 8) & 0xFF,
            pulses & 0xFF
        ]

        # Assemble full 7-byte command (Checksum is automatically appended by _send_cmd)
        # Payload: [Code(FD), Byte2, Byte3, Byte4, Byte5, Byte6, Byte7]
        cmd_payload = [0xFD, byte2, byte3, byte4_acc] + relpulses_bytes
        
        self._send_cmd(self.motor_id, cmd_payload)
        self.angle = target_angle
        print(f"[CAN Motor] Sent: FD {byte2:02X} {byte3:02X} {byte4_acc:02X} ... (Pulses: {pulses})")

        # self._send_cmd(0x01, [0xF6, 0x02, 0x80, 0x02])
        # self._send_cmd(0x00, [0x4B])


    def close(self):
        """Close CAN bus connection."""
        if self.bus:
            self.bus.shutdown()