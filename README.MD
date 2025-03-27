# PM Promoc_Assembly

A brief description of your project goes here.

## Table of Contents

- [Project Title](PM_Promoc_Assembly)
  - [Installation](#installation)
  - [Usage](#usage)
  - [Testing](#testing)
  - [Contributing](#contributing)
  - [License](#license)

## Installation

### 1. Create a ROS2 Workspace
   - Open a terminal and navigate to the directory where you want to create the ROS2 workspace.
   - Run the following command to create a new ROS2 workspace:

     ```bash
     mkdir -p ros2_ws/src
     cd ros2_ws
     ```

### 2. Clone the Project Repository
   - Inside the `src` directory of your ROS2 workspace, clone the project repository by running the following command:

     ```bash
     git clone <project_url>
     ```

### 3. Build the Project
   - Open a new terminal and navigate to the root of your ROS2 workspace.
   - Build the project with the following command:

     ```bash
     colcon build --symlink-install
     ```

  - Depending on your ROS2 version, you may encounter an error during the build due to the service messages. For ROS2 Humble, you need to comment out the `std_msgs` import, while for ROS2 Jazzy, it is required.


### 4. Source the ROS2 Setup File
   - After the build is complete, source the ROS2 setup file in the same terminal:

     - If you have configured it in your `.bashrc`, run:

       ```bash
       source .bashrc
       ```

     - Alternatively, source the workspace setup file directly:

       ```bash
       source ~/ros2_ws/install/setup.bash
       ```

   


## Usage

### How to Perform a Clean Build of Your ROS2 Workspace
   - Open a new terminal and navigate to the root of your ROS2 workspace.
   - To perform a clean build, remove the `build`, `install`, and `log` directories, which store built files and logs. Run the following commands:

     ```bash
     rm -rf build/ install/ log/
     ```

   - After cleaning, rebuild the workspace with:

     ```bash
     colcon build
     ```

   - Once the build is complete, remember to source the workspace again. For instructions, refer to step 4 in the **Installation** section.

### How to use the specific Nodes
  - To start the main node (e.g., mover_service_node), use the following command:
  ```bash
  ros2 run planar_motor_nodes mover_service_node
  ```
  - Once the node is running, you can send Service commands or monitor topics using tools like rqt or the ros_sequential_action_programmer. To run the ros_sequential_action_programmer, use:
  ```bash
  ros2 run ros_sequential_action_programmer ros_sequential_action_programmer
  ```

### How to use the Library Project at Home
  - The Service Node includes a parameter called use_simulation_mode. When this parameter is set to True, the code will bypass sections that require a connected PMC (Planar Motor Controller). This allows you to compile and run your code without the PMC being physically connected, making it easier to test and develop in a simulated environment.
  



## Testing

Instructions on how to run tests for your project.

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct, and the process for submitting pull requests to us.

## License

This project is licensed under the [MIT License](LICENSE).
