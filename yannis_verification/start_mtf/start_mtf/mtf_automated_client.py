import rclpy
from rclpy.node import Node
import time

# Korrekter Import der Service-Definition aus dem Interface-Paket
from promoc_assembly_interfaces.srv import MeasureMTF


class MTFAutomatedClient(Node):
    def __init__(self):
        super().__init__('mtf_automated_client')
        self.service_name = '/promoc/camera/measure_mtf'
        
        self.client = self.create_client(MeasureMTF, self.service_name)
        
        
        # Blockierende Schleife, bis der Server im Netzwerk registriert ist
        while not self.client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info(f'Warte auf Service {self.service_name}...')
        
        # Konstruktion der statischen Anfrage-Datenstruktur
        self.req = MeasureMTF.Request()
        
        self.req.measurement_mode = "capture_only"
        self.req.target_edge = "any" # wenns nicht geht nichts


    def set_camera_roi(self, config_id):
        # Dictionary mit allen Konfigurationen. 
        # Format: { ID: (x, y, width, height) }
        roi_configs = {
            # --- Cam 1 ---
            1: (2265, 1375, 1000, 1000),  # Mitte
            2: (1, 1, 1000, 1000),        # Oben links
            3: (4560, 1, 1000, 1000),     # Oben rechts
            4: (4560, 2770, 1000, 1000),  # Unten rechts
            5: (1, 2770, 1000, 1000),     # Unten links

            # --- Cam 2 ---
            6: (1436, 986, 1106, 1102),   # Mitte
            7: (1, 1, 1100, 1100),        # Oben links
            8: (2900, 1, 1100, 1100),     # Oben rechts
            9: (2900, 1900, 1100, 1100),  # Unten rechts
            10: (1, 1900, 1100, 1100),     # Unten links

            # --- Für 4x ---
            11: (2100, 1200, 1300, 1300),  # Mitte
            12: (1, 1, 1300, 1300),  # Oben links
            13: (4400, 1, 1300, 1300),  # Oben rechts
            14: (4400, 2500, 1300, 1300),  # Unten rechts
            15: (1, 2500, 1300, 1300), # Unten links

            # --- Für 1x ---
            16: (2400, 1400, 800, 800),  # Mitte
            17: (1, 1, 800, 800),  # Oben links
            18: (4900, 1, 800, 800),  # Oben rechts
            19: (4900, 3000, 800, 800),  # Unten rechts
            20: (1, 3000, 800, 800) # Unten links
        }

        # Prüfen, ob die übergebene Zahl im Dictionary existiert
        if config_id in roi_configs:
            # Werte entpacken und zuweisen
            x, y, w, h = roi_configs[config_id]
            
            self.req.roi_x = x
            self.req.roi_y = y
            self.req.roi_width = w
            self.req.roi_height = h
            
            print(f"Erfolg: ROI auf Setup {config_id} geändert.")
        else:
            print(f"Fehler: Die Nummer {config_id} ist nicht belegt. Bitte wähle eine Zahl zwischen 1 und 10.")


    def execute_measurements(self, iterations: int = 10):
        """Führt den Service-Aufruf sequenziell aus und loggt die optischen Kennzahlen."""
        self.get_logger().info(f'Initialisiere {iterations} MTF-Messungen.')
        erfolgreiche_messungen = 0

        while erfolgreiche_messungen < iterations:
            messung_id = erfolgreiche_messungen + 1
            self.get_logger().info(f'Starte Messung {messung_id}/{iterations}...')

            messung_erfolgreich = False
            max_versuche = 11 # 1 Erstversuch + max. 10 Wiederholungen
            
            for versuch in range(1, max_versuche + 1):
                if versuch > 1:
                    self.get_logger().warn(
                        f'Wiederholung {versuch - 1}/10 für Messung {messung_id}...'
                    )

                # Asynchrones Absenden der Anfrage
                future = self.client.call_async(self.req)
                
                # Die lokale Ausführung wird pausiert, bis der Server die Berechnung abschließt.
                # Dies führt dazu, dass keine parallelen Service-Aufrufe kollidieren.
                rclpy.spin_until_future_complete(self, future)
                
                response = future.result()
                
                # Auswertung und Validierung der Server-Antwort
                if response is not None and response.success:
                        messung_erfolgreich = True
                        erfolgreiche_messungen += 1
                        break
                else:
                    # Fehler- oder Netzwerkstatus bestimmen
                    status = response.status_message if response is not None else "Netzwerkfehler (keine Antwort)"
                    self.get_logger().error(f'Messung {messung_id} (Versuch {versuch}) fehlgeschlagen: {status}')
                    time.sleep(0.5)
            
            # Deterministische Hardware-Verzögerung
            # Gewährt dem Kamerasystem Zeit für die Stabilisierung von Framerate und Belichtung
            if not messung_erfolgreich:
                self.get_logger().error(
                    f'Messung {messung_id} nach {max_versuche - 1} Wiederholungen endgültig fehlgeschlagen. '
                    f'Messreihe wird abgebrochen.'
                )
                break
            
            # Standard-Verzögerung nach einer erfolgreichen Messung
            time.sleep(0.5)
            
            self.get_logger().info(f'Messreihe beendet. Erfolgreiche Messungen: {erfolgreiche_messungen}. ')

def main(args=None):
    rclpy.init(args=args)
    
    client_node = MTFAutomatedClient()
    client_node.set_camera_roi(19)
    #1: (2265, 1375, 1000, 1000),  # Mitte      209-211
    #2: (1, 1, 1000, 1000),        # Oben links
    #3: (4560, 1, 1000, 1000),     # Oben rechts
    #4: (4560, 2770, 1000, 1000),  # Unten rechts
    #5: (1, 2770, 1000, 1000),     # Unten links
    #6: (1436, 986, 1106, 1102),   # Mitte      209-211

    #11: (2100, 1200, 1300, 1300),  # Mitte
    #12: (1, 1, 1300, 1300),  # Oben links
    #13: (4400, 1, 1300, 1300),  # Oben rechts
    #14: (4400, 2500, 1300, 1300),  # Unten rechts
    #15: (1, 2500, 1300, 1300) # Unten links

    #16: (2400, 1400, 800, 800),  # Mitte
    #17: (1, 1, 800, 800),  # Oben links
    #18: (4900, 1, 800, 800),  # Oben rechts
    #19: (4900, 3000, 800, 800),  # Unten rechts
    #20: (1, 3000, 800, 800) # Unten links
    try:
        # Ausführen der Messreihe
        client_node.execute_measurements(100)
    except KeyboardInterrupt:
        client_node.get_logger().info('Messreihe durch Benutzerabbruch (Ctrl+C) beendet.')
    finally:
        client_node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
