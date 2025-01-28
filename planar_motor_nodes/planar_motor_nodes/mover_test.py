import rclpy
from mover_service_client import MoverServiceClient

def main(args=None):
    rclpy.init(args=args)
    client = MoverServiceClient()

    # Call the service functions with desired parameters
    response = client.call_linear_motion_service(1, 120.0, 120.0)
    
    
    
    if response.finished:
        print("Linear motion request finished successfully")
    else:
        print("Linear motion request failed")

    rclpy.shutdown()