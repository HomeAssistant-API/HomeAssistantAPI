###########
Usage
###########


The Basics...
#################

This library is centered around the :py:class:`Client` and :py:class:`WebsocketClient` classes.
Once you have have your api base url and Long Lived Access Token from Home Assistant we can start to do stuff.
The rest of this guide assumes you have the :py:class:`Client` saved to a :code:`client` variable or a :py:class:`WebsocketClient` saved to a :code:`ws_client` variable.
Most of these examples require some integrations to be setup inside Home Assistant for the examples to actually work.
The most commonly used features of this library include triggering services and getting and modifying entity states.

.. code-block:: python
    :linenos:

    import os
    from homeassistant_api import Client

    URL = '<API BASE URL>'  # Example: 'https://foobarhomeassistant.duckdns.org:8123/api'
    TOKEN = '<LONG LIVED ACCESS TOKEN>'

    # Assigns the Client object to a variable and checks if it's running.
    client = Client(URL, TOKEN)

    service = client.get_domain("light")  # Gets the light service domain from Home Assistant

    service.turn_on(entity_id="light.my_living_room_light")
    # Triggers the light.turn_on service on the entity `light.my_living_room_light`


.. code-block:: python
    :linenos:

    from homeassistant_api import WebsocketClient

    WS_URL = '<WS API BASE URL>'  # Example: 'https://foobarhomeassistant.duckdns.org:8123/api/websocket'
    TOKEN = '<LONG LIVED ACCESS TOKEN>'

    with WebsocketClient(WS_URL, TOKEN) as ws_client:  # opens a websocket connection to Home Assistant
        print(ws_client.render_template("{{ states('sensor.my_sensor') }}"))


.. code-block:: python
   :linenos:

    from datetime import datetime
    from homeassistant_api import Client

    # You can also initialize Client before you use it.

    client = Client("https://foobarhomeassistant.duckdns.org:8123/api", "mylongtokenpasswordthingyfoobar")

    # In order to activate the requests session you to use the Client context manager like so.
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

    # Alternatively you can set state from the entity class itself
    from homeassistant_api import State

    # If you are wondering where door came from its about 15 lines up.
    door.set_state(State(state="My new state", attributes={"open_height": "5ft"}))
    # <State "My new state" entity_id="cover.garage_door">

    ## All of these methods can be used with the WebsocketClient as well [except for set_state because the WS API doesn't support it :((( ].

Using Client with :code:`async`/:code:`await`
*************************************************
Are you wondering if you can use :code:`homeassistant_api` using Python's :code:`async`/:code:`await` syntax?
Good news! You can!

(You can't use the WebsocketClient with :code:`async`/:code:`await` yet because we haven't implemented it yet.)

Async Services
********************
.. code-block:: python

    import asyncio
    from homeassistant_api import Client

    # Initialize client like usual, except with the :code:`use_async` keyword.
    client = Client(url, token, use_async=True)

    async def main():

        domains = await client.async_get_domains()
        print(domains)
        # {'homeassistant': <Domain homeassistant>, 'notify': <Domain notify>}

        cover = await client.async_get_domain("cover")

        changed_states = await cover.close_cover(entity_id='cover.garage_door')
        # [<State "closing" entity_id="cover.garage_door">]

    asyncio.get_event_loop().run_until_complete(main())

Async Entities
*****************

.. code-block:: python

    entity_groups = await client.async_get_entities()
    # {'person': <Group person>, 'zone': <Group zone>, ...}

    door = await client.async_get_entity(entity_id='cover.garage_door')
    # <Entity entity_id="cover.garage_door" state="<yState "closed">">

    states = await client.async_get_states()
    # [<State "above_horizon" entity_id="sun.sun">, <State "zoning" entity_id="zone.home">,...]

    state = await client.async_get_state('sun.sun')
    # <State "above_horizon" entity_id="sun.sun">

    new_state = await client.async_set_state(
        State(
            state='my ToaTallY Whatever vAlUe 12t87932',
            entity_id='my_favorite_colors.number_one'
        )
    )
    # <State "my ToaTallY Whatever vAlUe 12t87932" entity_id="my_favorite_colors.number_one">

    # Alternatively you can set state from the entity class itself
    from homeassistant_api import State

    # If you are wondering where door came from its about 15 lines up.
    door.state.state = 'My new state'
    door.state.attributes.update({'open_height': '5ft'})
    await door.async_set_state(door.state)
    # <State "My new state" entity_id="cover.garage_door">


Using Events (Listening and Firing)
*****************************************

.. code-block:: python

    from homeassistant_api import WebsocketClient

    WS_URL = '<WS API BASE URL>'  # Example: 'https://foobarhomeassistant.duckdns.org:8123/api/websocket'
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
**************************

.. code-block:: python

    from homeassistant_api import WebsocketClient

    with WebsocketClient(WS_URL, TOKEN) as ws_client:
        with ws_client.listen_triggers() as triggers:  # see WebsocketClient.listen_triggers for more info.
            for trigger in triggers:
                print(trigger)
        
        # Another more specific example, listening for event triggers.
        with ws_client.listen_triggers("event", event_type="my_event") as triggers:
            ws_client.fire_event("my_event", my_arg="my_value")

            for trigger in triggers:
                print(trigger.variables.my_arg)  # This is the value of my_arg from the event fired above.

        # Another one, listening for time triggers.
        future = ws_client.get_rendered_template(
            "{{ (now() + timedelta(seconds=1)).strftime('%H:%M:%S') }}"
        )
        with ws_client.listen_trigger("time", at=future) as triggers:  # `at` can be HH:MM or HH:MM:SS
            print(next(triggers))

What's Next?
#############

Browse below to learn more about what you can do with :mod:`homeassistant_api`.

* `API Reference <api.html>`_
* `Advanced Section <advanced.html>`_
