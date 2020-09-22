import setuptools

setuptools.setup(
    name='guardicore-crawler',
    version='1.0.0',
    author='Yuval Ofer',
    packages=setuptools.find_packages(),
    description='A crawler that finds recursively all links from a given website',
    install_requires=[
        'requests==2.24.0',
        'bs4==0.0.1'
    ],
)
