.. Homeassistant API documentation master file, created by
   sphinx-quickstart on Wed Jul 14 00:58:24 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.


.. image:: ./images/homeassistant-logo.png

Welcome to Homeassistant API!
=============================

Homeassistant API is a pythonic module that interacts with `Homeassistant's REST API integration <https://developers.home-assistant.io/docs/api/rest>`_ and Homeassistant's `Websocket API <https://developers.home-assistant.io/docs/api/websocket>`_.
You can use it to remotely control your Home Assistant to do things like turn on lights, change the temperature, or listen for when the garage door opens.

Index
----------

.. toctree::
   :maxdepth: 1

   Home <self>
   quickstart
   usage
   api
   CONTRIBUTING
   Advanced <advanced>


Features
----------

1. Full consumption of the Home Assistant REST API endpoints.
2. Full consumption of the Home Assistant Websocket API (all of the documented commands and some undocumented ones).
3. Convenient Pydantic Models for data validation.
4. Synchronous and asynchronous support for both REST and WebSocket clients.
5. Modular design for intuitive readability.
6. Request caching for more efficient repetitive requests.

Getting Started
-------------------

Is this your first time using the library? Start with our :ref:`Quickstart Section <quickstart>`

Example
---------

.. literalinclude:: ../examples/basic.py
   :language: python

Want to look at more?
Many more examples are available in the :resource:`repository <examples>`.
We encourage you to open a pull request and add your own after you get to know the library!
See the :ref:`Contributing Section <contributing_section>`.


More Usage
---------------
View the documentation for each class and method :doc:`here <api>`.


.. _contributing_section:

Contributing Guidelines
--------------------------

We absolutely love contributions!
This library has come a long way since its one-file humble beginning on a Saturday afternoon.
However, while much has been done already there is still much much much more to do,
which is as exciting as it daunting!
If you're a developer that has an idea/suggestion or just wants to be helpful,
see our :ref:`Development and Contribution page <development_page>` for contribution ideas to get started, guidance, and what to expect with your PR.
Happy developing, and we hope to see your PRs soon.
