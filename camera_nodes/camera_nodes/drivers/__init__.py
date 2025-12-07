"""
Camera Drivers Package.

Dieses Package enthält die Treiber-Abstraktionsschicht für Kameras.

Verfügbare Treiber:
===================
    CameraDriver: Abstrakte Basis-Klasse (Interface-Definition)
    AravisCameraDriver: Echte Kamera via camera_aravis2 Treiber
    SimulatedCameraDriver: Simulator für Tests ohne Hardware

Verwendung:
===========
    from camera_nodes.drivers import CameraDriver, AravisCameraDriver
    
    # Treiber basierend auf Modus auswählen:
    if use_simulator:
        driver = SimulatedCameraDriver(logger)
    else:
        driver = AravisCameraDriver(node, logger)
"""

from .camera_driver import CameraDriver
from .aravis_camera_driver import AravisCameraDriver
from .simulated_camera_driver import SimulatedCameraDriver

__all__ = ['CameraDriver', 'AravisCameraDriver', 'SimulatedCameraDriver']
