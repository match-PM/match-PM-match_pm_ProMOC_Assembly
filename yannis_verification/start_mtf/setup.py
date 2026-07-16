from setuptools import find_packages, setup

package_name = 'start_mtf'

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
    maintainer="ProMOC Team",
    maintainer_email="promoc@match.uni-hannover.de",
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'run_mtf_client = start_mtf.mtf_automated_client:main',
            'grid_tracker = start_mtf.verschiebung:main',
            'verzeichnung = start_mtf.verzeichnung:main',
            'exposure_control = start_mtf.exposure_control:main',
        ],
    },
)
