from setuptools import setup, find_packages

package_name = 'verification'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Author',
    maintainer_email='user@todo.todo',
    description='Automated MTF measurement verification pipeline',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'verification_orchestrator = verification.verification_orchestrator:main',
            'mtf_verification = verification.mtf_verification_node:main',
            'scientific_verification = verification.scientific_verification_node:main',
        ],
    },
)
