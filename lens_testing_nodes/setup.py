from setuptools import find_packages, setup

package_name = 'lens_testing_nodes'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', [
            'launch/autofocus.launch.py',
            'launch/mtf_measurement.launch.py',
            'launch/full_measurement.launch.py',
        ]),
        ('share/' + package_name + '/config', [
            'config/autofocus_params.yaml',
            'config/mtf_params.yaml',
        ]),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Your Name',
    maintainer_email='your.email@match.uni-hannover.de',
    description='Lens Testing Nodes - Autofocus and MTF measurement for optical testing',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'autofocus_node = lens_testing_nodes.autofocus_node:main',
            'mtf_node = lens_testing_nodes.mtf_node:main',
            'hybrid_focus_node = lens_testing_nodes.hybrid_focus_node:main',
        ],
    },
)
