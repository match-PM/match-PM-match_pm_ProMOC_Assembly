import rclpy
from rclpy.node import Node
import time

# Korrekter Import der Service-Definition aus dem Interface-Paket
from promoc_assembly_interfaces.srv import MeasureMTF


class MTFAutomatedClient(Node):
    def __init__(self):
        super().__init__('mtf_automated_client')
        
        # Initialisierung des Service-Clients.
        # Hinweis: Verwende hier den exakten Service-Namen. Du hast zuvor
        # '/promoc/camera/measure_mtf_roi' in der Liste gefunden. 
        # Falls es auch '/promoc/camera/measure_mtf_center' gibt, tausche den String entsprechend aus.
        #self.service_name = '/promoc/camera/measure_mtf_center'
        self.service_name = '/promoc/camera/measure_mtf'
        ''' 
        # Anpassung an die neue Struktur des MTF-Services:
        self.service_name = '/promoc/camera/measure_mtf'


        Falls du auch AF nutzen möchtest z.b nach 50 Messungen einmal refokusierne oder so, kannst du auch den gleich einen AF CLienten erstellen und die entsprechenden Anfragen vorbereiten.

        self.af_client = self.create_client(AutofocusROI, '/promoc/camera/autofocus_roi')

        self.af_req = AutofocusROI.Request() 


        '''
        

        self.client = self.create_client(MeasureMTF, self.service_name)
        
        
        # Blockierende Schleife, bis der Server im Netzwerk registriert ist
        while not self.client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info(f'Warte auf Service {self.service_name}...')
        
        # Konstruktion der statischen Anfrage-Datenstruktur
        self.req = MeasureMTF.Request()
        
        self.req.measurement_mode = "capture_only"
        self.req.target_edge = "any" # wenns nicht geht nichts
        
        # Parameter
        self.req.roi_x = 2722
        self.req.roi_y = 1749
        self.req.roi_width = 1000
        self.req.roi_height = 1000
        '''
        # AF Parameter falls du den nutzen möchtest
        self.af_req.start_position = 275
        self.af_req.end_position = 285
        self.af_req.focus_mode = 0
        self.af_req.skip_flyover = True
        
        self.af_req.roi_x = self.req.roi_x 
        self.af_req.roi_y = self.req.roi_y 
        self.af_req.roi_width = self.req.roi_width 
        self.af_req.roi_height = self.req.roi_height 
        '''
        

    def execute_measurements(self, iterations: int = 100):
        """Führt den Service-Aufruf sequenziell aus und loggt die optischen Kennzahlen."""
        self.get_logger().info(f'Initialisiere {iterations} MTF-Messungen.')
        
        for i in range(iterations):
            self.get_logger().info(f'Starte Messung {i+1}/{iterations}...')
            
            # Asynchrones Absenden der Anfrage
            future = self.client.call_async(self.req)
            
            # Die lokale Ausführung wird pausiert, bis der Server die Berechnung abschließt.
            # Dies führt dazu, dass keine parallelen Service-Aufrufe kollidieren.
            rclpy.spin_until_future_complete(self, future)
            
            response = future.result()
            
            # Auswertung und Validierung der Server-Antwort
            if response is not None:
                if response.success:
                    self.get_logger().info(
                        f'Ergebnis {i+1} | '
                        f'MTF50: {response.mtf50:.2f} lp/mm | '
                        f'Winkel: {response.edge_angle:.2f}°'
                    )
                else:
                    self.get_logger().error(f'Messung {i+1} fehlgeschlagen: {response.status_message}')
            else:
                self.get_logger().error(f'Service-Aufruf {i+1} lieferte keine Antwort (Netzwerkfehler).')
            
            # Deterministische Hardware-Verzögerung
            # Gewährt dem Kamerasystem Zeit für die Stabilisierung von Framerate und Belichtung
            time.sleep(0.5)

def main(args=None):
    rclpy.init(args=args)
    
    client_node = MTFAutomatedClient()
    
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
