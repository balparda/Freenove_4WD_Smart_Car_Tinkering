# Balparda's Mods to 4W Car

https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/
https://docs.python-guide.org/dev/virtualenvs/
https://pipenv.pypa.io/en/latest/basics/
https://realpython.com/python-virtual-environments-a-primer/
https://setuptools.pypa.io/en/latest/userguide/quickstart.html

## Making an Usable Build Environment

Start with:

```
$ sudo apt-get install tox python3-venv python3-setuptools python3-build
```

Create `pyproject.toml` exactly like:

```
[build-system]
requires = ["setuptools"]
build-backend = "setuptools.build_meta"
```

Create `tox.ini` like:

```
[tox]
envlist = py36,py39
isolated_build = true
[testenv]
platform = linux
deps =
    numpy >= 1.19  # example
    ... etc ...
    pytest
commands =
    # NOTE: you can run any command line tool here - not just tests
    pytest
[testenv:py36]
basepython=/path/to/my/Python-3.6.0/python  # point to an alternate version
[testenv:dev]  # only if needed!!
    basepython = py39
    usedevelop = true
    commands = ... etc ...
    deps = ... etc ...
```

Create `setup.cfg` like:

```
[metadata]
name = project-name
version = 0.1
[options]
packages = project-pack  # python packages in the project ( __init__.py)
install_requires =
    numpy >= 1.19  # example
    ... etc ...
setup_requires =
    wheel
```

Use this setup like:

```
$ tox
[... runs all *_test.py in project ...]

$ source .tox/py39/bin/activate
[enters a bash mode where python and deps are controlled]

$ pip list
Package          Version
---------------- -------
attrs            21.4.0
numpy            1.22.2
...etc...

$ python Path/To/my_main.py
[this will execute the code in controlled environment]

$ deactivate
[back to normal bash]
```

To build a python version, do:

```
sudo apt-get install build-essential checkinstall
sudo apt-get install libncursesw5-dev libssl-dev libsqlite3-dev tk-dev libgdbm-dev libc6-dev libbz2-dev
wget https://www.python.org/ftp/python/3.6.0/Python-3.6.0.tar.xz
tar xvf Python-3.6.0.tar.xz
cd Python-3.6.0/
./configure --enable-optimizations
make
```
