from setuptools import find_packages, setup

package_name = "camera_nodes"

setup(
    name=package_name,
    version="0.0.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/config", ["config/camera.yaml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="ProMOC Team",
    maintainer_email="promoc@match.uni-hannover.de",
    description="Camera runtime for raw image publishing and status reporting",
    license="MIT",
    entry_points={
        "console_scripts": [
            "camera_node = camera_nodes.node:main",
        ],
    },
)
