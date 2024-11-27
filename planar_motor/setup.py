from setuptools import find_packages, setup

package_name = 'planar_motor'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools',
                      'pythonnet',
                      'pmclib'
                      ],
    zip_safe=True,
    maintainer='pmlab_mover',
    maintainer_email='pmlab_mover@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            "mover_node = planar_motor.mover_node:main",
            "mover_service_node = planar_motor.mover_service_node:main",
            "mover_client_node = planar_motor.mover_client_node:main"
        ],
    },
)
