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

- Full consumption of the Home Assistant REST API endpoints.
- Full consumption of the Home Assistant Websocket API (all of the documented commands and some undocumented ones)
- Convenient Pydantic Models for data validation.
- Syncrononous and Asynchronous support for integrating with all applications and/or libraries.
- Modular design for intuitive readability.
- Request caching for more efficient repeative requests.

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

We absolutely looooooooooove contributions!
This library has come a long way since its one-file humble beginning, on a Saturday afternoon with some our programming buddies.
But while much has been done already there is still much much much more to do!
Which is exciting!
If you're a developer that has an idea, suggestion or just wants to be helpful because you're an awesome person.
See our \*newly minted\* :ref:`Development and Contribution page <development_page>` for contribution ideas, guidelines, procedures and what to expect with your PR.
Happy developing!
We hope to see your PRs soon.

..
   We would love to give a special shoutout to `FoxNerdSaysMoo <https://github.com/FoxNerdSaysMoo>` for contributions to some of the awesome theme styling on these docs!
