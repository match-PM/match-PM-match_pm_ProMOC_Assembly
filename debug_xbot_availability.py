#!/usr/bin/env python3
"""
Debug script to test XBot availability with real PMCLib.
Run this before and after motions to see when XBot data becomes unavailable.
"""

import sys
import os
import time

# Add the package to path
sys.path.insert(0, '/home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/planar_motor_nodes')

from planar_motor_nodes.pmclib_loader import bot, sys_cmd, get_pmclib_status

def test_xbot_availability():
    """Test which XBots are available and responding."""
    print("🔍 Testing XBot availability...")
    
    # Check PMCLib status
    status = get_pmclib_status()
    print(f"📊 PMCLib Status: {status}")
    
    if status['is_mock']:
        print("⚠️ Using mock PMCLib - this test is for real PMCLib only")
        return
    
    print("\n1️⃣ Testing get_all_xbot_info() with different feedback options:")
    for feedback_opt in [0, 1, 2]:
        try:
            data_list = bot.get_all_xbot_info(feedback_opt)
            count = len(data_list) if data_list else 0
            print(f"   Feedback option {feedback_opt}: {count} XBots")
            
            if data_list and count > 0:
                for i, data in enumerate(data_list):
                    try:
                        pos = [data.x_pos, data.y_pos, data.z_pos]
                        print(f"     XBot {i}: position = {pos}")
                    except AttributeError as e:
                        print(f"     XBot {i}: ERROR reading position - {e}")
        except Exception as e:
            print(f"   Feedback option {feedback_opt}: ERROR - {e}")
    
    print("\n2️⃣ Testing individual XBot status calls:")
    for xbot_id in range(4):  # Test first 4 XBot IDs
        try:
            status = bot.get_xbot_status(xbot_id)
            print(f"   XBot {xbot_id}: Status available, state = {status.xbot_state}")
        except Exception as e:
            print(f"   XBot {xbot_id}: ERROR - {e}")
    
    print("\n3️⃣ Testing individual XBot position calls:")
    for xbot_id in range(4):
        try:
            data_list = bot.get_all_xbot_info(0)  # Position feedback
            if data_list and len(data_list) > xbot_id:
                data = data_list[xbot_id]
                pos = [data.x_pos, data.y_pos, data.z_pos]
                print(f"   XBot {xbot_id}: position = {pos}")
            else:
                print(f"   XBot {xbot_id}: No data in get_all_xbot_info")
        except Exception as e:
            print(f"   XBot {xbot_id}: ERROR - {e}")

def test_motion_impact():
    """Test the impact of a small motion on XBot availability."""
    print("\n🎯 Testing motion impact on XBot availability...")
    
    status = get_pmclib_status()
    if status['is_mock']:
        print("⚠️ Using mock PMCLib - motion test skipped")
        return
    
    try:
        # Connect if not already connected
        print("🔗 Ensuring connection...")
        success = sys_cmd.connect_to_pmc("192.168.10.100")
        if not success:
            print("❌ Failed to connect to PMC")
            return
        
        # Activate XBots
        print("🔄 Activating XBots...")
        bot.activate_xbots()
        time.sleep(2)
        
        print("\n📍 BEFORE MOTION:")
        test_xbot_availability()
        
        # Perform a small motion
        print("\n🚀 Performing small linear motion...")
        try:
            # Small motion: move 1mm in X direction
            result = bot.linear_motion_si(0.001, 0.0, 0.0, 0)  # XBot 0
            print(f"   Motion command result: {result}")
            time.sleep(1)  # Wait for motion to complete
        except Exception as e:
            print(f"   Motion command failed: {e}")
        
        print("\n📍 AFTER MOTION:")
        test_xbot_availability()
        
        # Try another motion on XBot 1
        print("\n🚀 Performing motion on XBot 1...")
        try:
            result = bot.linear_motion_si(0.001, 0.0, 0.0, 1)  # XBot 1
            print(f"   Motion command result: {result}")
            time.sleep(1)
        except Exception as e:
            print(f"   Motion command on XBot 1 failed: {e}")
        
        print("\n📍 AFTER XBot 1 MOTION:")
        test_xbot_availability()
        
    except Exception as e:
        print(f"❌ Motion test failed: {e}")

if __name__ == "__main__":
    print("🔍 XBot Availability Debug Tool")
    print("=" * 50)
    
    try:
        test_xbot_availability()
        
        # Ask user if they want to test motion impact
        response = input("\n❓ Test motion impact? (y/n): ").lower().strip()
        if response == 'y':
            test_motion_impact()
            
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n✅ Debug test completed")
