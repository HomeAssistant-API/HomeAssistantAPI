.. _development_page:

*****************
Contributing
*****************

This page is where development related things are.
See below.

Contribution Ideas
*********************

If you don't know what you want to contribute yet you should take a look at our :resource:`issues page <issues>`.
See what other people have been up to and if you have an idea for a new feature or a new way to implement a feature you should :resource:`create an issue <issues>` or :resource:`fork the repository <repo>` and start contributing.
We're always interested in integrating ways to make the library faster, extensible and easier to use.

Setting up your Development Environment
*****************************************

So now that you know what you want to contribute it is time to setup a development environment to make your changes in.

Step One: Fork the Repository
===============================

Click `here <https://github.com/GrandMoff100/HomeAssistantAPI/fork>`__ to fork the repository.
Then click your username.

Step Two: Clone the Repository Locally
=======================================

Next run in your terminal.

.. code-block:: bash

   $ git clone https://github.com/<YOUR_GITHUB_USERNAME>/HomeAssistantAPI

Step Three: Installing Dependencies
======================================

Firstly, you need to have Python 3.11 or newer installed.
Download the latest Python Version from `here <https://www.python.org/>`__.
Then you need to install :code:`uv`, a fast Python package manager.
Checkout the `uv Docs <https://docs.astral.sh/uv/>`__.
You can install it with :code:`pip` by running :code:`pip install uv`, or see the uv docs for other installation methods.
Now you can install the project's dependencies by running :code:`cd HomeAssistantAPI && uv sync`

Step Four: [Optional] Setting Up a Home Assistant Development Environment.
=============================================================================

If you do not have a Home Assistant installation running already, you can setup a Home Assistant Development environment.
Which is basically a local, unpackaged, Home Assistant Core installation, that runs with just Python (no Docker or Operating System).
You can start and stop the server really easily as it runs just in your
terminal and gives you lots of control over it, making it ideal for testing your changes to Home Assistant API.
Follow this great guide `here <https://developers.home-assistant.io/docs/development_environment>`__ to do that.
After that you are now ready to make your changes to the codebase!

Testing
********
In order to test your changes you need to have an API URL, and a Long Lived Access Token.
Follow the :ref:`Quickstart Section <access_token_setup>` for getting those.
If you setup the Development Environment then your API URL will most likely be something along the lines of :code:`https://localhost:8123/api`.
Then you can test your changes by passing the API URL, and Long Lived Access Token to the :class:`homeassistant_api.Client` object.

.. _styling:

Code Styling Guidelines
**************************

In order to make sure that our code is easy to read, and navigate.
As well as to stop stupid mistakes like typos, undefined variables, etc.
We enforce code standards.
Using the tools, :code:`ruff`, :code:`zuban`, :code:`pytest`, and :code:`docker`, we make make sure that our code quality is top notch, and that are changes work everywhere.
You can those tools manually yourself, but they also run automatically when you open a PR.

Merging Your Contributions
*****************************

Once you have tested your changes and committed them to your fork you can merge them back into the :resource:`original repository <repo>`.
Head over to the :resource:`Pull Request Page <new_pr>` and select your fork to merge into the `GrandMoff100/dev` branch.
Then you can hit "Create Pull Request" and we'll review it as soon as possible.
In order to be merged though, your code needs to follow our :ref:`Styling Guidelines <styling>`.
A Github Actions workflow will run on your PR automatically to verify that it does follow the guidelines.
Then once the checks have passed one of our maintainers will review the changes (basically to make sure your changes won't break anything ;)).
Then after that your changes will get merged and will be available in the next release!

