import json
import xml.etree.ElementTree as ET

# Fichiers d'entrée/sortie
input_json = "export.json"
output_osm = "routetunis_raw.osm"

with open(input_json, "r", encoding="utf-8") as f:
    data = json.load(f)

# Création de la racine OSM
osm = ET.Element("osm", version="0.6", generator="overpass-json-to-osm")

nodes = {}
next_node_id = -1

# Créer les noeuds lat/lon pour chaque élément avec géométrie
for element in data.get("elements", []):
    if element.get("type") in ("way", "relation"):
        geom = element.get("geometry")
        if not geom:
            continue
        for g in geom:
            key = (g["lat"], g["lon"])
            if key not in nodes:
                node_id = next_node_id
                next_node_id -= 1
                nodes[key] = node_id
                ET.SubElement(osm, "node", id=str(node_id),
                              lat=str(g["lat"]), lon=str(g["lon"]))

# Créer les ways à partir des éléments avec géométrie
for element in data.get("elements", []):
    if element.get("type") == "way":
        geom = element.get("geometry")
        if not geom:
            continue
        way = ET.SubElement(osm, "way", id=str(element["id"]))
        # reconstruire nd
        for g in geom:
            key = (g["lat"], g["lon"])
            node_id = nodes[key]
            ET.SubElement(way, "nd", ref=str(node_id))
        # tags
        for k, v in element.get("tags", {}).items():
            ET.SubElement(way, "tag", k=k, v=v)

# Écrire le fichier OSM
tree = ET.ElementTree(osm)
tree.write(output_osm, encoding="utf-8", xml_declaration=True)

print(f"Fichier OSM généré : {output_osm}")
