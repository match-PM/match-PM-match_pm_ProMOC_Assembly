from setuptools import setup, find_packages

package_name = "promoc_core"

setup(
    name=package_name,
    version="0.0.0",
    packages=find_packages(),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="ProMOC Team",
    maintainer_email="promoc@match.uni-hannover.de",
    description="Shared logging, error handling, and validation helpers for ProMOC Messstand",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [],
    },
)
