.. _development_page:

*****************
Contributing
*****************

This page is where development related things are.
See below.

Contribution Ideas
*********************

If you don't know what you want to contribute yet you should take a look at our :resource:`issues page <issues>`.
Some other places to start with are:

- **Writing and Rewriting Documentation**--- As more code changes happen and this library continues to mature, more features get added which need documenting.
- **Adding examples**--- We'd appreciate more self-contained examples that show common use cases.

See what other people have been up to all across the home assistant community and if you have an idea for a new feature you should :resource:`create an issue <issues>` or :resource:`fork the repository <repo>` and start contributing.
We're always interested in integrating ways to make the library faster, extensible and easier to use.

Setting up your Development Environment
*****************************************

So now that you know what you want to contribute it is time to setup a development environment to make your changes in.

Step One: Fork the Repository
===============================

Click :resource:`here <fork>` to fork the repository.
Then click your username.

Step Two: Clone the Repository Locally
=======================================

Next run in your terminal.

.. code-block:: bash

   $ git clone https://github.com/<YOUR_GITHUB_USERNAME>/HomeAssistantAPI

Step Three: Installing Dependencies
======================================

Firstly, you need to have Python 3.11 or newer installed.
Download the latest Python Version from `here <https://www.python.org/>`__ (or your usual method of installation).
Then you need to install :code:`uv`, a fast Python package manager.
Checkout the `uv Docs <https://docs.astral.sh/uv/>`__.
You can install it with :code:`pip` by running :code:`pip install uv`, or see the uv docs for other installation methods.
Now you can install the project's dependencies by running :code:`cd HomeAssistantAPI && uv sync`

Step Four: [Optional] Setting Up a Home Assistant Server
=============================================================================

Option A. Have a Home Assistant installation running.
------------------------------------------------------

If you already have a Home Assistant installation running, you can use it for development.
You'll just need to have the API URL and a Long-Lived Access Token available like you would to use the library normally.


Option B. Setup a Home Assistant Development Environment.
----------------------------------------------------------

If you do not have a Home Assistant installation running already, you can setup a Home Assistant Development environment.
This is basically a local, unpackaged, Home Assistant Core installation, that runs with just Python (no Docker or Operating System).
You can start and stop the server really easily as it runs just in your
terminal and gives you control over it, making it ideal for quickly testing your changes.
Follow this great guide `here <https://developers.home-assistant.io/docs/development_environment>`__ to do that.
You'll access the web dashboard to create the Long-Lived Access Token.


Option C. Use a Docker-based Development Environment.
-----------------------------------------------------

If you prefer to use Docker, you can use your own Docker setup to run a Home Assistant development environment.
There is also a Dockerfile and compose file that comes with the repository to make it convenient to spin up a development environment.
To do so, you can run

.. code-block:: bash

   $ docker compose up server

which spins up a container running Home Assistant with port 8123 exposed to your local machine.
You'll need the following environment variables set to use the repository docker setup:

.. code-block:: bash

   HOMEASSISTANTAPI_URL=http://localhost:8123/api
   HOMEASSISTANTAPI_WS_URL=ws://localhost:8123/api/websocket
   HOMEASSISTANTAPI_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJkMDE4YjQ4YzMyZTE0ODNhYjY2ZWQzOTZmYzg3ZDAyNiIsImlhdCI6MTY3ODU3NDUwMSwiZXhwIjoxOTkzOTM0NTAxfQ.fyhnfwpont4uE0gn46_Ut_pPmyn4QWv0MDaVAei2PPk



Testing
********

Tests use pre-recorded cassettes so you do **not** need a running Home Assistant instance to run the test suite.
Each test has its own cassette stored under :code:`tests/cassettes/<module>/<test_name>.json`.

Running the test suite
=======================

.. code-block:: bash

   $ uv run pytest

Recording cassettes for a new test
=====================================

If you add a new test that makes real HTTP or WebSocket requests, you need to record its cassette against a live Home Assistant instance.

1. Get an API URL and a Long-Lived Access Token by following the :ref:`Quickstart Section <access_token_setup>`.
2. Export the environment variables:

   .. code-block:: bash

      $ export HOMEASSISTANTAPI_URL="http://<your-ha-host>:8123/api"
      $ export HOMEASSISTANTAPI_WS_URL="ws://<your-ha-host>:8123/api/websocket"
      $ export HOMEASSISTANTAPI_TOKEN="<your-token>"

3. Run pytest with the :code:`--record` flag to record cassettes:

   .. code-block:: bash

      $ uv run pytest --record

   This records a fresh :code:`.json` cassette for every test.
   Commit the cassette files alongside your test so CI can replay them without a live server.

.. _styling:

Code Styling Guidelines
**************************

In order to make sure that our code is easy to read, and navigate
as well as to stop stupid mistakes like typos, undefined variables, etc,
we enforce code standards.
Using the tools, :code:`ruff`, :code:`zuban`, and :code:`pytest`, we make sure that our code quality is top notch and that changes work everywhere.
You can run those tools manually yourself, but they also run automatically when you open a Pull Request on :resource:`GitHub <repo>`.


Merging Your Contributions
*****************************

Once you have tested your changes and committed them to your fork you can merge them back into the :resource:`original repository <repo>`.
Head over to the :resource:`Pull Request Page <new_pr>` and select your fork to merge into the main branch.
Then you can hit "Create Pull Request" and we'll review it as soon as possible.
In order to be merged, a Github Actions workflow will run on your PR automatically, to check that your code passes the styling checks and tests.
Then once the checks have passed, one of our maintainers will review the changes and ask for clarification or changes (if needed).
Then after that your changes will get merged and will be available in the next release!

