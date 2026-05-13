###########
Usage
###########


The Basics...
#################

This library provides four client classes:

- :py:class:`Client` — sync REST API client
- :py:class:`AsyncClient` — async REST API client
- :py:class:`WebsocketClient` — sync WebSocket client
- :py:class:`AsyncWebsocketClient` — async WebSocket client

Once you have your API base URL and Long Lived Access Token from Home Assistant we can start to do stuff.
The rest of this guide assumes you have a client saved to a variable as shown below.
Most of these examples require some integrations to be setup inside Home Assistant for the examples to actually work.
The most commonly used features of this library include triggering services and getting and modifying entity states.

.. code-block:: python
    :linenos:

    import os
    from homeassistant_api import Client

    URL = '<API BASE URL>'  # Example: 'http://homeassistant.local:8123/api'
    TOKEN = '<LONG LIVED ACCESS TOKEN>'

    # Assigns the Client object to a variable and checks if it's running.
    client = Client(URL, TOKEN)

    service = client.get_domain("light")  # Gets the light service domain from Home Assistant

    service.turn_on(entity_id="light.my_living_room_light")
    # Triggers the light.turn_on service on the entity `light.my_living_room_light`


.. code-block:: python
    :linenos:

    from homeassistant_api import WebsocketClient

    WS_URL = '<WS API BASE URL>'  # Example: 'ws://homeassistant.local:8123/api/websocket'
    TOKEN = '<LONG LIVED ACCESS TOKEN>'

    with WebsocketClient(WS_URL, TOKEN) as ws_client:  # opens a websocket connection to Home Assistant
        print(ws_client.get_rendered_template("{{ states('sensor.my_sensor') }}"))


.. code-block:: python
   :linenos:

    from datetime import datetime
    from homeassistant_api import Client

    # You can also initialize Client before you use it.

    client = Client("http://homeassistant.local:8123/api", "mylongtokenpasswordthingyfoobar")

    # In order to activate the requests session you need to use the Client context manager like so.
    # Using it as a context manager will automatically close the session when you're done with it.
    # But also will *ping* your Home Assistant instance to make sure it's running.
    with client:
        while True:
            sun = client.get_entity(entity_id="sun.sun")
            state = sun.get_state()  # Because requests are cached we reduce bandwidth usage :D
            # Cache expires every 30 seconds by default.
            if state.state == "below_horizon":
                difference = datetime.now() - state.last_updated
                print("Sun set", difference.seconds, "seconds ago.")
                break

Services
**********

.. code-block:: python

    light = client.get_domain("light")

    print(light.services)
    # {'turn_on': Service(service_id='turn_on', name='Turn on', description='Turn on one or more lights and adjust properties of the light, even when they are turned on already.\n', ...

    changed_states = light.toggle(entity_id="light.light_bulb_1")

.. code-block:: python

    climate = ws_client.get_domain("climate")

    print(climate.services)
    # {'set_temperature': Service(service_id='set_temperature', name='Set temperature', description='Set the target temperature for a climate entity.\n', ...

    changed_states = climate.set_temperature(entity_id="climate.my_thermostat", temperature=72)

Entities
*************

.. code-block:: python

    entity_groups = client.get_entities()
    # {'person': <Group person>, 'zone': <Group zone>, ...}

    door = client.get_entity(entity_id='cover.garage_door')
    # <Entity entity_id="cover.garage_door" state="<State "closed">">

    states = client.get_states()
    # [<State "above_horizon" entity_id="sun.sun">, <State "zoning" entity_id="zone.home">,...]

    state = client.get_state('sun.sun')
    # <State "above_horizon" entity_id="sun.sun">

    new_state = client.set_state(
        State(state='my ToaTallY Whatever vAlUe 12t87932', entity_id='my_favorite_colors.number_one')
    )
    # <State "my ToaTallY Whatever vAlUe 12t87932" entity_id="my_favorite_colors.number_one">

    # Alternatively you can update state from the entity class itself.
    # Modify the entity's local state object, then push it to Home Assistant.
    door.state.state = 'My new state'
    door.state.attributes.update({'open_height': '5ft'})
    door.update_state()
    # <State "My new state" entity_id="cover.garage_door">

    # All of these methods work with the WebsocketClient as well.


Using the :py:class:`WebsocketClient`
****************************************

Using Events (Listening and Firing)
------------------------------------

.. code-block:: python

    from homeassistant_api import WebsocketClient

    WS_URL = '<WS API BASE URL>'  # Example: 'ws://homeassistant.local:8123/api/websocket'
    TOKEN = '<LONG LIVED ACCESS TOKEN>'

    with WebsocketClient(WS_URL, TOKEN) as ws_client:
        with ws_client.listen_events() as events:
            for event in events:
                print(event)

        # Or if you want to listen for a specific event type until dinner time.
        with ws_client.listen_events('state_changed') as events:
            for event in events:
                print(event)
                if event.data.entity_id == 'myalarmclock.dinner_time' and event.data.new_state.state == 'now':
                    break

        # Or if you want to listen for just 10 events.
        with ws_client.listen_events("my_event") as events:
            for _, event in zip(range(10), events):
                print(event)

        # Alternatively for just one event.
        with ws_client.listen_events("my_event") as events:
            event = next(events)
            print(event)

        # Now to fire an event.
        ws_client.fire_event("my_event", my_arg="my_value")


Listening for Triggers
-------------------------

.. code-block:: python

    from homeassistant_api import WebsocketClient

    with WebsocketClient(WS_URL, TOKEN) as ws_client:
        with ws_client.listen_trigger() as triggers:  # see WebsocketClient.listen_trigger for more info.
            for trigger in triggers:
                print(trigger)

        # Another more specific example, listening for event triggers.
        with ws_client.listen_trigger("event", event_type="my_event") as triggers:
            ws_client.fire_event("my_event", my_arg="my_value")

            for trigger in triggers:
                print(trigger.variables.my_arg)  # This is the value of my_arg from the event fired above.

        # Another one, listening for time triggers.
        future = ws_client.get_rendered_template(
            "{{ (now() + timedelta(seconds=1)).strftime('%H:%M:%S') }}"
        )
        with ws_client.listen_trigger("time", at=future) as triggers:  # `at` can be HH:MM or HH:MM:SS
            print(next(triggers))


Using :py:class:`AsyncClient`
*********************************
All four client classes share the same method names.
The async clients (:py:class:`AsyncClient` and :py:class:`AsyncWebsocketClient`) simply use :code:`async def` methods that you :code:`await`.

Async Services
********************
.. code-block:: python

    import asyncio
    from homeassistant_api import AsyncClient

    async def main():
        async with AsyncClient(url, token) as client:
            domains = await client.get_domains()
            print(domains)
            # {'homeassistant': <AsyncDomain homeassistant>, 'notify': <AsyncDomain notify>}

            cover = await client.get_domain("cover")

            changed_states = await cover.close_cover(entity_id='cover.garage_door')
            # (<State "closing" entity_id="cover.garage_door">,)

    asyncio.run(main())

Async Entities
*****************

.. code-block:: python

    entity_groups = await client.get_entities()
    # {'person': <AsyncGroup person>, 'zone': <AsyncGroup zone>, ...}

    door = await client.get_entity(entity_id='cover.garage_door')
    # <AsyncEntity entity_id="cover.garage_door" state="<State "closed">">

    states = await client.get_states()
    # (<State "above_horizon" entity_id="sun.sun">, <State "zoning" entity_id="zone.home">,...)

    state = await client.get_state('sun.sun')
    # <State "above_horizon" entity_id="sun.sun">

    new_state = await client.set_state(
        State(
            state='my ToaTallY Whatever vAlUe 12t87932',
            entity_id='my_favorite_colors.number_one'
        )
    )
    # <State "my ToaTallY Whatever vAlUe 12t87932" entity_id="my_favorite_colors.number_one">

    # Alternatively you can update state from the entity class itself.
    door.state.state = 'My new state'
    door.state.attributes.update({'open_height': '5ft'})
    await door.update_state()
    # <State "My new state" entity_id="cover.garage_door">

Async WebSocket
******************

The :py:class:`AsyncWebsocketClient` works the same way:

.. code-block:: python

    import asyncio
    from homeassistant_api import AsyncWebsocketClient

    async def main():
        async with AsyncWebsocketClient(ws_url, token) as ws_client:
            template = await ws_client.get_rendered_template("{{ states('sensor.my_sensor') }}")
            print(template)

    asyncio.run(main())


What's Next?
#############

Browse below to learn more about what you can do with :mod:`homeassistant_api`.

* `API Reference <api.html>`_
* `Advanced Section <advanced.html>`_
