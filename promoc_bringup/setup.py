from setuptools import setup
import os
from glob import glob

package_name = 'promoc_bringup'

setup(
    name=package_name,
    version='0.2.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
        (os.path.join('share', package_name, 'config', 'cameras'), glob('config/cameras/*.yaml')),
        # Include URDF files
        (os.path.join('share', package_name, 'urdf', 'assemblies'),
            glob('urdf/assemblies/*.xacro')),
        (os.path.join('share', package_name, 'urdf', 'modules'),
            glob('urdf/modules/*.xacro')),
        (os.path.join('share', package_name, 'urdf', 'properties'),
            glob('urdf/properties/*.xacro')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ProMOC Team',
    maintainer_email='promoc@match.uni-hannover.de',
    description='ProMOC Assembly launch files and utilities',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            # Optional demo controller. Not a canonical startup path.
            'unified_demo = promoc_bringup.unified_demo:main',
        ],
    },
)
