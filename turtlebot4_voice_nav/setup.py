from setuptools import setup
from glob import glob

name = 'turtlebot4_voice_nav'
setup(name=name, version='0.1.0', packages=[name],
      data_files=[('share/ament_index/resource_index/packages', ['resource/'+name]),
                  ('share/'+name, ['package.xml', 'README.md', 'LICENSE']),
                  *[('share/'+name+'/'+folder, glob(folder+'/*')) for folder in ['launch', 'maps', 'config']]],
      install_requires=['setuptools'], zip_safe=True,
      maintainer='Student', maintainer_email='student@example.com',
      description='Semantic regions and Vietnamese speech navigation', license='Apache-2.0',
      entry_points={'console_scripts': [
          'voice_navigator = turtlebot4_voice_nav.navigator:main',
          'voice_dashboard = turtlebot4_voice_nav.dashboard:main',
          'segment_map = turtlebot4_voice_nav.segmentation:main']})
