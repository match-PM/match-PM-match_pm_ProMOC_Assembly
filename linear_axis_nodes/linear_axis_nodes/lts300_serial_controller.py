import serial
import time
import logging

# Konfiguriere das Logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class LTS300Controller:
    def __init__(self, port, baudrate=115200, timeout=1):
        """
        Initialisiert die serielle Verbindung zum LTS300-Motorcontroller.

        :param port: Der COM-Port (z. B. "COM3" unter Windows oder "/dev/ttyUSB0" unter Linux).
        :param baudrate: Die Baudrate (standardmäßig 115200).
        :param timeout: Timeout für die serielle Kommunikation in Sekunden.
        """
        try:
            self.ser = serial.Serial(port, baudrate, timeout=timeout)
            logging.info(f"Verbunden mit {port} bei {baudrate} Baud.")
        except serial.SerialException as e:
            logging.error(f"Fehler beim Verbinden mit {port}: {e}")
            raise

    def send_command(self, command):
        """
        Sendet einen seriellen Befehl an den LTS300.

        :param command: Der zu sendende Befehl als Byte-Array.
        """
        try:
            self.ser.write(command)
            logging.debug(f"Befehl gesendet: {command.hex()}")
        except serial.SerialException as e:
            logging.error(f"Fehler beim Senden des Befehls: {e}")
            raise

    def read_response(self, expected_length=6, max_attempts=5, delay=0.1):
        """
        Liest die Antwort vom LTS300.

        :param expected_length: Die erwartete Länge der Antwort (standardmäßig 6).
        :param max_attempts: Maximale Anzahl von Leseversuchen.
        :param delay: Verzögerung zwischen den Leseversuchen in Sekunden.
        :return: Die Antwort als Byte-Array.
        """
        for attempt in range(max_attempts):
            try:
                response = self.ser.read(expected_length)
                if len(response) == expected_length:
                    logging.debug(f"Antwort empfangen: {response.hex()}")
                    return response
                elif len(response) > 0:
                    logging.warning(f"Unvollständige Antwort empfangen: {response.hex()}")
                else:
                    logging.warning(f"Keine Antwort empfangen (Versuch {attempt + 1}/{max_attempts})")
            except serial.SerialException as e:
                logging.error(f"Fehler beim Lesen der Antwort: {e}")
            time.sleep(delay)

        raise ValueError(f"Keine gültige Antwort nach {max_attempts} Versuchen")

    def home_motor(self, channel=1):
        """
        Startet den Homing-Prozess für den angegebenen Kanal.

        :param channel: Der Kanal, für den der Homing-Prozess gestartet werden soll (standardmäßig 1).
        """
        logging.info(f"Starte Homing-Prozess für Kanal {channel}")
        home_command = bytes([0x43, 0x04, channel, 0x00, 0x22, 0x01])
        self.send_command(home_command)

        max_attempts = 10
        for attempt in range(max_attempts):
            try:
                response = self.read_response()
                if response[0] == 0x44 and response[1] == 0x04 and response[2] == channel:
                    logging.info(f"Homing für Kanal {channel} abgeschlossen.")
                    return
                else:
                    logging.warning(f"Unerwartete Antwort: {response.hex()}")
            except ValueError as e:
                logging.error(f"Fehler beim Lesen der Antwort: {e}")

            logging.debug(f"Warte vor dem nächsten Versuch (Versuch {attempt + 1}/{max_attempts})")
            time.sleep(1)

        raise TimeoutError(f"Homing-Prozess nicht abgeschlossen nach {max_attempts} Versuchen")
    def move_absolute(self, position, channel=1):
        """
        Bewegt den Motor auf eine absolute Position.

        :param position: Die Zielposition.
        :param channel: Der Kanal, für den die Bewegung durchgeführt werden soll (standardmäßig 1).
        """
        # MGMSG_MOT_MOVE_ABSOLUTE (0x0453)
        move_command = bytes([0x53, 0x04, channel, 0x00]) + position.to_bytes(4, byteorder='little')
        self.send_command(move_command)

    def move_relative(self, distance, channel=1):
        """
        Bewegt den Motor um eine relative Distanz.

        :param distance: Die relative Distanz.
        :param channel: Der Kanal, für den die Bewegung durchgeführt werden soll (standardmäßig 1).
        """
        # MGMSG_MOT_MOVE_RELATIVE (0x0448)
        move_command = bytes([0x48, 0x04, channel, 0x00]) + distance.to_bytes(4, byteorder='little')
        self.send_command(move_command)

    def stop_motor(self, channel=1):
        """
        Stoppt den Motor sofort.

        :param channel: Der Kanal, für den der Motor gestoppt werden soll (standardmäßig 1).
        """
        # MGMSG_MOT_STOP (0x0464)
        stop_command = bytes([0x64, 0x04, channel, 0x00, 0x01, 0x00])
        self.send_command(stop_command)

    def close(self):
        """
        Schließt die serielle Verbindung.
        """
        try:
            self.ser.close()
            logging.info("Serielle Verbindung geschlossen.")
        except Exception as e:
            logging.error(f"Fehler beim Schließen der seriellen Verbindung: {e}")

# Test code
if __name__ == "__main__":
    controller = None
    try:
        logging.info("Starte Test des LTS300Controllers")
        controller = LTS300Controller("/dev/ttyUSB0")
        controller.home_motor()
        logging.info("Test erfolgreich abgeschlossen")
    except Exception as e:
        logging.error(f"Ein Fehler ist aufgetreten: {e}", exc_info=True)
    finally:
        if controller:
            controller.close()
