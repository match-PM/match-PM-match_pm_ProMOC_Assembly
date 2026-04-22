from setuptools import find_packages, setup

package_name = "planar_motor_nodes"

setup(
    name=package_name,
    version="0.0.0",
    packages=find_packages(exclude=["test", "*/__pycache__", "__pycache__"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    include_package_data=True,
    maintainer="ProMOC Team",
    maintainer_email="promoc@match.uni-hannover.de",
    description="ROS2 nodes for planar motor control with PMCLib integration",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "mover_node = planar_motor_nodes.node:main",
        ],
    },
)
