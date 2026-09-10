from setuptools import find_packages, setup

package_name = "camera_nodes"

setup(
    name=package_name,
    version="0.0.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools", "matplotlib"],
    zip_safe=True,
    maintainer="ProMOC Team",
    maintainer_email="promoc@match.uni-hannover.de",
    description="Camera services for autofocus, MTF measurement, and exposure control",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "camera_node = camera_nodes.node:main",
            "target_tilt_estimator = camera_nodes.target_tilt_node:main",
            "target_tilt_repeatability = camera_nodes.tilt_repeatability:main",
            "mtf_batch_analyze = camera_nodes.mtf_batch_analyze:main",
            "measurement_runner = camera_nodes.measurement_runner:main",
            "measurement_analyze = camera_nodes.measurement_analyze:main",
        ],
    },
)
