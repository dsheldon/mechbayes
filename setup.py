from setuptools import find_packages, setup

setup(
    name='mechbayes',
    version="0.0.1",
    description='Bayesian COVID-19 models',
    packages=find_packages(include=['mechbayes', 'mechbayes.*']),
    url='https://github.com/dsheldon/mechbayes',
    author='Dan Sheldon',
    author_email='sheldon@cs.umass.edu',
    install_requires=[
        'numpyro>=0.4.1'
        'jax>=0.2.3'
    ],
    keywords='machine learning bayesian statistics',
    license='MIT'
)
