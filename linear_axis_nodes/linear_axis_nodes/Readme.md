ertainly! Below is the revised README content formatted as a code block:

markdown
# ROS 2 Node Setup for Windows and Ubuntu

## Prerequisites: CycloneDDS Configuration

Ensure that CycloneDDS is used on both Windows and Ubuntu platforms. Below is a sample XML configuration file for CycloneDDS:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<CycloneDDS xmlns="https://cdds.io/config" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="https://cdds.io/config https://raw.githubusercontent.com/eclipse-cyclonedds/cyclonedds/master/etc/cyclonedds.xsd">
    <Domain id="any">
        <General>
            <Interfaces>
                <NetworkInterface address="YOUR_IP"/>
            </Interfaces>
            <AllowMulticast>default</AllowMulticast>
            <MaxMessageSize>65500B</MaxMessageSize>
            <FragmentSize>4000B</FragmentSize>
        </General>
        <Discovery>
            <Peers>
                <Peer address="YOUR_IP"/>
                <Peer address="OTHER_IP"/>
            </Peers>
            <ParticipantIndex>auto</ParticipantIndex>
            <MaxAutoParticipantIndex>120</MaxAutoParticipantIndex>
        </Discovery>
        <Tracing>
            <Verbosity>warning</Verbosity>
            <OutputFile>stdout</OutputFile>
        </Tracing>
    </Domain>
</CycloneDDS>
```

Replace `YOURIP` and `OTHERIP` with the correct IP addresses applicable to your network setup.
Setup Instructions for Windows

1. Open Terminal:
   - Launch Tabby Terminal with Administrator privileges.

2. Developer Command Prompt:
   - Click on the terminal icon at the top and choose the "Developer Prompt for VS2019".

3. Source ROS 2 Installation & Workspace:
   ```bash
   call C:\dev\ros2_jazzy\setup.bat
   call C:\Users\admin\promoc_ros2_ws\install\setup.bat
   ```

4. Navigate to Workspace:
   ```bash
   cd C:\Users\admin\promoc_ros2_ws
   ```

5. Build the Workspace:
   ```bash
   colcon build --merge-install
   ```
   - For detailed build output, use:
   ```bash
   colcon build --merge-install --event-handlers console_direct+
   ```

6. Run the Node:
   ```bash
   ros2 run linear_axis_nodes lts300_service_node
   ```

This guide provides a structured approach to setting up and running a ROS 2 node on Windows using CycloneDDS, ensuring proper configuration and execution within your development environment.
``
