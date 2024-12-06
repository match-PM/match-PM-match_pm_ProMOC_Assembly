from setuptools import find_packages, setup

package_name = 'match-PM-match_pm_ProMOC_Assembly'

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
    maintainer='C.Sternberg',
    maintainer_email='C.Sternberg@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            "mover_service_node = nodes.planar_motor.mover_service_node:main",
            "mover_client_node = nodes.planar_motor.mover_client_node:main"
        ],
    },
)
