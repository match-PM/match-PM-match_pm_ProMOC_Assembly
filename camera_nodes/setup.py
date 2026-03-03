from setuptools import find_packages, setup

package_name = 'camera_nodes'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='pmlab',
    maintainer_email='thesterni91@gmail.com',
    description='Camera services for autofocus, MTF measurement, and exposure control',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'camera_node = camera_nodes.camera_node:main',
            'camera_simulator = camera_nodes.camera_simulator:main',
            'camera_watchdog = camera_nodes.camera_watchdog:main'
        ],
    },
)
