from setuptools import find_packages, setup

package_name = 'linear_axis_nodes'

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
    maintainer='promoc',
    maintainer_email='promoc@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'lts300_service_node = linear_axis_nodes.lts300_service_node:main'
            'lts300_z_axis_node = linear_axis_nodes.lts300_z_axis_node:main'
        ],
    },
)

