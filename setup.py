from setuptools import setup

setup(name='CausalDeepCENT',
      version='0.1',
      description='Weighted Causal Deep Learning for Prediction of Individual Event Times',
      url='http://github.com/yicjia/CausalDeepCENT',
      author='Yichen Jia',
      author_email='yij22@pitt.edu',
      license='MIT',
      packages=['CausalDeepCENT'],
      install_requires=[
          'pandas','numpy','torch','keras',
          'lifelines','sklearn','scipy'
      ],
      zip_safe=False)
