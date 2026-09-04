from glob import glob
import os

from setuptools import setup


package_name = "promoc_bringup"

setup(
    name=package_name,
    version="0.2.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        (os.path.join("share", package_name, "launch"), glob("launch/*.py")),
        (os.path.join("share", package_name, "config"), glob("config/*.yaml")),
        (os.path.join("share", package_name, "config", "measurement_plans"),
         glob("config/measurement_plans/*.yaml") + glob("config/measurement_plans/*.csv")),
        (
            os.path.join("share", package_name, "config", "cameras"),
            glob("config/cameras/*.yaml"),
        ),
        (
            os.path.join("share", package_name, "config", "imaging_profiles"),
            glob("config/imaging_profiles/*.yaml"),
        ),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="ProMOC Team",
    maintainer_email="promoc@match.uni-hannover.de",
    description="ProMOC measurement-stand launch files and utilities",
    license="MIT",
    tests_require=["pytest"],
    entry_points={"console_scripts": []},
)
