tf2idle is a Python library to idle in `Team Fortress 2 <http://teamfortress.com>`_ using Sandboxie.

*Warning: This project is in early stages of development. Expect major changes!*


Quickstart
----------

Login to your Steam accounts (you will be prompted to enter a password)::

    $ tf2idlectl.py login --usernames steamaccount1 steamaccount2
    Enter password for steamaccount1:
    Enter password for steamaccount2:

Then launch TF2 to begin idling::

    $ tf2idlectl.py launchtf2 --usernames steamaccount1 steamaccount2

To stop idling you can either close TF2 (and remain logged into Steam)::

    $ tf2idlectl.py closetf2 --usernames steamaccount1 steamaccount2

or logout of Steam::

    $ tf2idlectl.py logout --usernames steamaccount1 steamaccount2


Supported Python versions
~~~~~~~~~~~~~~~~~~~~~~~~~

Python 3.2+ is currently supported.


Installation
------------

First you must install `Sandboxie <http://sandboxie.com>`_ on your machine.

Next install the development branch with `pip <http://pip-installer.org>`_::

    $ pip install git+https://github.com/gg/tf2idle@development


Running the Tests
~~~~~~~~~~~~~~~~~

tox_ is used to run unit and integration tests in each of the supported Python
environments.

First install tox_::

    $ pip install tox

Then run tox_ from the project root directory::

    $ tox

.. _tox: http://tox.testrun.org/


Contribute
----------

The code repository is on GitHub: https://github.com/gg/tf2idle.

To contribute:

#. Work on an `open issue`_ or submit a new issue to start a discussion around
   a bug or feature request.

    * When submitting a bug, ensure your description includes the following:
        - the version you are using
        - any relevant system information, such as your operating system
        - steps to produce the bug (so others could reproduce it)

#. Fork `the repository`_ and add the bug fix or feature to the **develop**
   branch.
#. Write tests that demonstrate the bug was fixed or the feature works as
   expected.
#. Submit a pull request and bug the maintainer until your contribution gets
   merged and published :-) You should also add yourself to AUTHORS_.

.. _the repository: https://github.com/gg/tf2idle
.. _open issue: https://github.com/gg/tf2idle/issues
.. _AUTHORS: https://github.com/gg/tf2idle/blob/develop/AUTHORS.rst


Coding Style
~~~~~~~~~~~~

Ensure that your contributed code complies with `PEP 8`_. The test runner
tox_ will automatically check for PEP 8 compliance.

.. _PEP 8: http://www.python.org/dev/peps/pep-0008/
