/* RR27 corridor extract for the DSDA testbed (protocol v1.0, section 2).
   Run in https://overpass-turbo.eu, then Export > raw OSM data (JSON). */
[out:json][timeout:180][bbox:36.42,10.74,36.63,10.92];
(
  way["highway"~"^(motorway|trunk|primary|secondary|tertiary|unclassified|residential|living_street|service|track|road)(_link)?$"];
  way["waterway"];
  way["name"];
  node["name"];
  node["place"];
  relation["route"="road"];
);
out geom;
