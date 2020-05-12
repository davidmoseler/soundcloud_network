# Soundcloud Network
Build a network of the user relationships from soundcloud

![Image of a soundcloud graph](https://github.com/davidmoseler/soundcloud_network/blob/master/Soundcloud%20Graph.png)

This code scans the soundcloud api to build a graph of user relationships (who he follows, who is he followed by), in order to better identify musical trends, genres, clusters, and influential people.

If you want to run the code, you need a soundcloud client_id and client_secret from the soundcloud api. Setup a neo4j database, and then edit the settings.ini file with the information. Add an initial uri to start scanning, like https://soundcloud.com/username. Now you can run it with

```python
python soundcloud_user.py
```
