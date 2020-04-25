# coding=utf-8
from setuptools import setup

setup(
    name='srgs-grammar-validation',
    packages=['grammarvalidation'],
    package_data={'grammarvalidation': ['*.xsd']},
    scripts=[
        'bin/srgsvalidation',
    ],
    install_requires=[
        'click==7.0',
        'colorama==0.4.3',
        'lxml==4.3.1',
        'six==1.12.0',
        'typing==3.6.6',
        'cchardet==2.1.5'
    ],
    version='DEVELOPMENT',
    url='https://github.com/VSHUMILIN97/srgs-validation',
    license='MIT',
    author='Vadim Shumilin',
    author_email='vshumilin1488@gmail.com',
    description='Библиотека и утилита для проверки SRGS грамматик'
)
