from setuptools import find_packages, setup

package_name = 'promoc_nodes'

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
    maintainer='pmlab_mover',
    maintainer_email='pmlab_mover@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            "mover_service_node = promoc_nodes.planar_motor.mover_service_node:main",
            "mover_client_node = promoc_nodes.planar_motor.mover_client_node:main"
        ],
    },
)
