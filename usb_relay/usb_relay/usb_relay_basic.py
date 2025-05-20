#!/home/pm_control/Documents/PyVenv/promocVenv/bin/python
import hid
import time


VENDOR_ID = 0x16c0  # Beispiel Vendor-ID
PRODUCT_ID = 0x05df  # Beispiel Product-ID
#vendor_id': 5824, 'product_id': 1503,
VENDOR_ID = 5824  # Beispiel Vendor-ID
PRODUCT_ID = 1503  # Beispiel Product-ID

def connection_relay(VENDOR_ID, PRODUCT_ID):
    device = hid.device()
    device.open(VENDOR_ID, PRODUCT_ID)
    return device


def disconnetion_relay(device):
    device.close()


def set_relay_state(device, relay_number, state):
    if state:
        device.write([0, 0xFF, relay_number, 0, 0, 0, 0, 0, 1])
    else:
        device.write([0, 0xFD, relay_number, 0, 0, 0, 0, 0, 1])


def set_all_on(device):
    device.write([0, 0xFE, 0, 0, 0, 0, 0, 0, 1])


def set_all_off(device):
    device.write([0, 0xFC, 0, 0, 0, 0, 0, 0, 1])


def read_all(device):
    # res = device.read(8)    
    # receive_buffer = bytearray( res )
    print(device.read(8))

# def read_from_device(device, size=64):
#     try:
#         # Lese "size" Bytes vom Gerät
#         data = device.read(size)

#         # Überprüfen, ob Daten empfangen wurden
#         if data:
#             print(f"Empfangene Daten: {data}")
#         else:
#             print("Keine Daten empfangen.")

#         return data
#     except Exception as e:
#         print(f"Fehler beim Lesen der Daten: {e}")
#         return None


def read_from_device(device, size, timeout=5):
    start_time = time.time()
    device.set_nonblocking(2)  # Setze das Gerät in den nicht-blockierenden Modus
    while True:
        try:
            # Lese "size" Bytes vom Gerät
            data = device.read(size)
            print(f"Empfangene Daten: {data}")
            if data:
                print(f"Empfangene Daten: {data}")
                return data

            # Überprüfe, ob das Timeout erreicht wurde
            if time.time() - start_time > timeout:
                print("Timeout beim Lesen der Daten.")
                return None

            # Kurze Pause, um die CPU-Last zu reduzieren
            time.sleep(0.1)
        except Exception as e:
            print(f"Fehler beim Lesen der Daten: {e}")
            return None
    

    



if __name__ == '__main__':
    # count = 1
    # for dev in hid.enumerate():
    #    print(str(count) + ": ")
    #    print(dev)
    #    print("\n")
    #    count = count + 1
    
    sizeVec = [1, 2, 3, 4, 5, 6, 7, 8]#, 9, 18, 32, 64, 96, 128, 156]

    device = connection_relay(VENDOR_ID=VENDOR_ID, PRODUCT_ID=PRODUCT_ID)

    set_all_off(device=device)

    # for i in range(1, 9):
    #     set_relay_state(device=device, relay_number=i, state=True)
    #     read_from_device(device=device, size=18)

    #     time.sleep(1)

    set_relay_state(device=device, relay_number=1, state=True)
    set_relay_state(device=device, relay_number=6, state=True)
    

    for i in sizeVec:#range(64, 129):
        print("Size: " + str(i))
        read_from_device(device=device, size=i)
        time.sleep(0.5)
    
    time.sleep(2)

    set_all_off(device=device)

    disconnetion_relay(device=device)