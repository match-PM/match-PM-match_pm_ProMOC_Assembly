from setuptools import find_packages, setup

package_name = 'nodes'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        # Dateien, die in den Ressourcenindex von Ament eingefügt werden
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        # Die package.xml wird im Installationsverzeichnis des Pakets platziert
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='sterni',
    maintainer_email='thesterni91@gmail.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'test_node = nodes.test_nodes.test_node:main',  # Beispiel für einen Node
        ],
    },
    
)