import serial
import time
import argparse
from datetime import datetime, timezone

UBX_HEADER = b"\xB5\x62"
g_set_sequence = 0

def ubx_checksum(data):
    ck_a = 0
    ck_b = 0

    for b in data:
        ck_a = (ck_a + b) & 0xFF
        ck_b = (ck_b + ck_a) & 0xFF

    return bytes([ck_a, ck_b])

def make_ubx(cls_id, msg_id, payload):
    body = bytes([cls_id, msg_id]) + len(payload).to_bytes(2, "little") + payload
    return UBX_HEADER + body + ubx_checksum(body)

def get_device_info(ser):
    ser.write(bytes.fromhex("B5 62 0A 04 00 00 0E 34"))
    payload = bytes([])
    cmd = make_ubx(0x0A, 0x04, payload)
    ser.write(cmd)
    return

def set_nmea_rate(ser, sequence):

    if sequence == 0:
        # GSA OFF
        payload = bytes([0xF0, 0x02, 0,0,0,0,0,0])
        cmd = make_ubx(0x06, 0x01, payload)
        ser.write(cmd)
    elif sequence == 1:
        # VTG OFF
        payload = bytes([0xF0, 0x05, 0,0,0,0,0,0])
        cmd = make_ubx(0x06, 0x01, payload)
        ser.write(cmd)
    elif sequence == 2:
        # GSV OFF
        payload = bytes([0xF0, 0x03, 0,0,0,0,0,0])
        cmd = make_ubx(0x06, 0x01, payload)
        ser.write(cmd)
    elif sequence == 3:
        # GLL OFF
        payload = bytes([0xF0, 0x01, 0,0,0,0,0,0])
        cmd = make_ubx(0x06, 0x01, payload)
        ser.write(cmd)
    elif sequence == 4:
        # measurement_period = 100ms
        payload = bytes([0x64, 0x00, 0x01, 0x00, 0x00, 0x00])
        cmd = make_ubx(0x06, 0x08, payload)
        ser.write(cmd)

    return


def parse_ubx(ser, msg):
    global g_set_sequence

    cls = msg[2]
    mid = msg[3]
    length = int.from_bytes(msg[4:6], "little")
    payload = msg[6:6+length]

    print(f"UBX : cls={cls:02X} id={mid:02X} len={length}")

    # MON-VER
    if cls == 0x0A and mid == 0x04:
        print("  MON-VER : " + payload.decode("ascii", errors="ignore"))
        set_nmea_rate(ser, g_set_sequence)
    elif cls == 0x05 and mid == 0x01:
        g_set_sequence += 1
        set_nmea_rate(ser, g_set_sequence)


def print_log(text):
    ms = int(time.time() * 1000)
    dt = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
    formatted = dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    print(f"{formatted} : {text}")


def receieve_loop(ser):
    global g_set_sequence

    buffer = b""
    g_set_sequence = 0
    while True:
        buffer += ser.read(32)
        while buffer:
            if buffer.startswith(b"$"):
                end = buffer.find(b"\r\n")
                if end == -1:
                    break

                line = buffer[:end]
                buffer = buffer[end+2:]
                print_log("NMEA:" + line.decode(errors="ignore"))

            elif buffer.startswith(b"\xB5\x62"):
                length = int.from_bytes(buffer[4:6], "little")
                total = 6 + length + 2

                if len(buffer) < total:
                    print(f"total={total} > len(buffer)={len(buffer)}")
                    break

                msg = buffer[:total]
                buffer = buffer[total:]

                parse_ubx(ser, msg)

            # ----------------------------
            # ゴミスキップ
            # ----------------------------
            else:
                print(f"Garbage:[{buffer[0]}]")
                buffer = buffer[1:]



def main():
    parser = argparse.ArgumentParser(description="Set UBX GNSS receiver rate.")
    parser.add_argument("port", help="COM port to use (e.g., COM4)")
    args = parser.parse_args()

    ser = serial.Serial(args.port, 9600)

    get_device_info(ser)
    receieve_loop(ser)

    return

print(f"__name__:{__name__}")
if __name__ == "__main__":
    main()
