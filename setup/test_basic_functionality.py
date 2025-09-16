#!/usr/bin/env python3
"""
Basic functionality test for ProMOC Assembly system
Tests imports, service definitions, and basic node instantiation
"""

import sys
import os

# Add local libs to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'local_libs'))


def test_service_interfaces():
    """Test that all service interfaces are available"""
    print("Testing service interfaces...")

    try:
        from promoc_assembly_interfaces.srv import (
            # Planar motor services
            ActivateXbots, LevitationXbots, LinearMotionSi,
            RotaryMotion, SixDofMotion, StopMotion, SetVelocityAcceleration,
            ArcMotionSi,
            # Linear axis services
            MoveAbsolute, MoveRelativ, Home, ShutdownLinearAxis,
            GetPosition, GetSetHomingParams, GetSetVelocityParams
        )
        print("✓ All service interfaces imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Service interface import failed: {e}")
        return False


def test_mock_pmclib():
    """Test mock PMCLib functionality"""
    print("Testing mock PMCLib...")

    try:
        from planar_motor_nodes.drivers.mock_pmclib import MockPMCLib
        mock_lib = MockPMCLib()
        print("✓ MockPMCLib imported and instantiated successfully")
        return True
    except Exception as e:
        print(f"✗ MockPMCLib test failed: {e}")
        return False


def test_response_formats():
    """Test that service responses follow the standardized format"""
    print("Testing standardized response formats...")

    try:
        from promoc_assembly_interfaces.srv import ActivateXbots, MoveAbsolute

        # Test planar motor service response
        pm_response = ActivateXbots.Response()
        if hasattr(pm_response, 'success') and hasattr(pm_response, 'status_message'):
            print("✓ Planar motor service has standardized response format")
        else:
            print("✗ Planar motor service missing standardized response fields")
            return False

        # Test linear axis service response
        la_response = MoveAbsolute.Response()
        if hasattr(la_response, 'success') and hasattr(la_response, 'status_message'):
            print("✓ Linear axis service has standardized response format")
        else:
            print("✗ Linear axis service missing standardized response fields")
            return False

        return True
    except Exception as e:
        print(f"✗ Response format test failed: {e}")
        return False


def test_camera_integration():
    """Test camera integration package and external dependencies"""
    print("Testing camera integration package...")
    
    try:
        # Test if camera_aravis2 is available in workspace
        import subprocess
        import os
        
        workspace_root = os.path.expanduser("~/ros2_ws")
        camera_aravis2_path = os.path.join(workspace_root, "src", "camera_aravis2")
        
        if os.path.exists(camera_aravis2_path):
            print("✓ camera_aravis2 repository found in workspace")
        else:
            print("⚠ camera_aravis2 repository not found")
            print("  Run: cd ~/ros2_ws/src && git clone https://github.com/FraunhoferIOSB/camera_aravis2.git")
            return False
        
        # Test if our camera_nodes package can be imported (after build)
        try:
            from camera_nodes.camera_manager import CameraManager
            print("✓ Camera nodes package available")
        except ImportError:
            print("⚠ Camera nodes package not yet built")
            print("  Run: colcon build --packages-select camera_nodes")
            
        return True
        
    except Exception as e:
        print(f"✗ Camera integration test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("ProMOC Assembly System - Basic Functionality Test")
    print("=" * 50)

    tests = [
        test_service_interfaces,
        test_mock_pmclib,
        test_response_formats,
        test_camera_integration,  # Add camera test
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()

    print("=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("✓ All basic functionality tests PASSED")
        return 0
    else:
        print("✗ Some tests FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
