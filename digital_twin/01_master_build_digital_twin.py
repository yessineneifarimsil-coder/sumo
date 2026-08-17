#!/usr/bin/env python3
"""
MASTER SCRIPT: Build Complete Digital Twin for Route de Tunis
"""

import xml.etree.ElementTree as ET
import json
from datetime import datetime

# ============================================================================
# PART 1: TRAFFIC ANALYSIS ZONES (TAZs)
# ============================================================================

TAZS = {
    "TAZ1_ResidentialNorth": {
        "centroid_lat": 35.81,
        "centroid_lon": 10.76,
        "land_use": "Residential",
        "population_estimate": 45000,
        "households": 9000,
        "description": "Apartment blocks, family homes (North of corridor)",
        "vehicle_generation_rate": 10,
        "peak_hour_percentage": 0.08,
        "primary_destinations": ["TAZ3_CommercialCenter", "TAZ8_BusinessDistrict"],
    },

    "TAZ2_ResidentialSouth": {
        "centroid_lat": 35.78,
        "centroid_lon": 10.76,
        "land_use": "Residential",
        "population_estimate": 38000,
        "households": 7600,
        "description": "Housing suburbs (South of corridor)",
        "vehicle_generation_rate": 10,
        "peak_hour_percentage": 0.08,
        "primary_destinations": ["TAZ3_CommercialCenter", "TAZ4_PortArea"],
    },

    "TAZ3_CommercialCenter": {
        "centroid_lat": 35.795,
        "centroid_lon": 10.76,
        "land_use": "Commercial/Mixed Use",
        "area_m2": 2800000,
        "employees": 8000,
        "businesses": 450,
        "description": "Shops, malls, offices (Downtown Sfax)",
        "vehicle_generation_rate": 40,
        "peak_hour_percentage": 0.10,
        "primary_destinations": [
            "TAZ1_ResidentialNorth",
            "TAZ2_ResidentialSouth",
            "TAZ4_PortArea",
            "TAZ5_IndustrialWest",
        ],
    },

    "TAZ4_PortArea": {
        "centroid_lat": 35.79,
        "centroid_lon": 10.77,
        "land_use": "Port/Industrial",
        "area_m2": 1500000,
        "employees": 2500,
        "containers_per_day": 800,
        "description": "Port facilities, cargo handling, logistics",
        "vehicle_generation_rate": 20,
        "peak_hour_percentage": 0.09,
        "primary_destinations": ["TAZ3_CommercialCenter", "TAZ5_IndustrialWest"],
        "heavy_vehicle_percentage": 0.35,
    },

    "TAZ5_IndustrialWest": {
        "centroid_lat": 35.80,
        "centroid_lon": 10.75,
        "land_use": "Industrial",
        "area_m2": 2000000,
        "employees": 3500,
        "factories": 45,
        "description": "Manufacturing, warehouses, logistics centers",
        "vehicle_generation_rate": 5,
        "peak_hour_percentage": 0.08,
        "primary_destinations": ["TAZ3_CommercialCenter", "TAZ4_PortArea"],
        "heavy_vehicle_percentage": 0.40,
    },

    "TAZ6_Airport": {
        "centroid_lat": 35.82,
        "centroid_lon": 10.75,
        "land_use": "Transportation/Airport",
        "area_m2": 800000,
        "annual_passengers": 2000000,
        "daily_flights": 40,
        "description": "Sfax-Thyna airport, access and parking",
        "vehicle_generation_rate": 50,
        "peak_hour_percentage": 0.12,
        "primary_destinations": ["TAZ3_CommercialCenter", "TAZ1_ResidentialNorth"],
        "taxi_percentage": 0.25,
    },

    "TAZ7_University": {
        "centroid_lat": 35.78,
        "centroid_lon": 10.77,
        "land_use": "Education",
        "area_m2": 1200000,
        "students": 8000,
        "staff": 1200,
        "description": "University campus, student housing, services",
        "vehicle_generation_rate": 2,
        "peak_hour_percentage": 0.09,
        "primary_destinations": ["TAZ1_ResidentialNorth", "TAZ2_ResidentialSouth"],
    },

    "TAZ8_BusinessDistrict": {
        "centroid_lat": 35.795,
        "centroid_lon": 10.77,
        "land_use": "Office/Business",
        "area_m2": 900000,
        "employees": 5000,
        "companies": 120,
        "description": "Corporate offices, headquarters, professional services",
        "vehicle_generation_rate": 20,
        "peak_hour_percentage": 0.09,
        "primary_destinations": ["TAZ3_CommercialCenter"],
    },
}

# ============================================================================
# PART 2: VEHICLE TYPES
# ============================================================================

VEHICLE_TYPES = {
    "car_aggressive": {
        "id": "car_aggressive",
        "vClass": "passenger",
        "length": 5.0,
        "minGap": 2.5,
        "maxSpeed": 50,
        "accel": 3.0,
        "decel": 5.0,
        "sigma": 0.15,
        "tau": 0.8,
        "speedFactor": 1.1,
        "speedDev": 0.1,
        "lcStrategic": 1.0,
        "lcCooperative": 0.5,
        "description": "Aggressive drivers: taxi, delivery (15%)",
        "percentage_of_traffic": 0.15,
    },

    "car_normal": {
        "id": "car_normal",
        "vClass": "passenger",
        "length": 5.0,
        "minGap": 3.0,
        "maxSpeed": 50,
        "accel": 2.6,
        "decel": 4.5,
        "sigma": 0.26,
        "tau": 1.0,
        "speedFactor": 1.0,
        "speedDev": 0.15,
        "lcStrategic": 0.5,
        "lcCooperative": 0.8,
        "description": "Normal drivers: commuters (65%)",
        "percentage_of_traffic": 0.65,
    },

    "car_cautious": {
        "id": "car_cautious",
        "vClass": "passenger",
        "length": 5.0,
        "minGap": 3.5,
        "maxSpeed": 50,
        "accel": 2.0,
        "decel": 3.5,
        "sigma": 0.35,
        "tau": 1.2,
        "speedFactor": 0.9,
        "speedDev": 0.20,
        "lcStrategic": 0.2,
        "lcCooperative": 0.5,
        "description": "Cautious drivers: elderly (20%)",
        "percentage_of_traffic": 0.20,
    },

    "bus_intercity": {
        "id": "bus_intercity",
        "vClass": "bus",
        "length": 12.0,
        "minGap": 4.0,
        "maxSpeed": 45,
        "accel": 1.5,
        "decel": 3.5,
        "sigma": 0.10,
        "tau": 1.3,
        "speedFactor": 0.9,
        "speedDev": 0.05,
        "description": "Long-distance buses (RTC)",
        "capacity": 50,
    },

    "bus_urban": {
        "id": "bus_urban",
        "vClass": "bus",
        "length": 10.5,
        "minGap": 3.5,
        "maxSpeed": 45,
        "accel": 1.8,
        "decel": 3.5,
        "sigma": 0.12,
        "tau": 1.2,
        "speedFactor": 0.9,
        "speedDev": 0.08,
        "description": "Urban buses",
        "capacity": 40,
    },

    "taxi": {
        "id": "taxi",
        "vClass": "taxi",
        "length": 5.2,
        "minGap": 2.5,
        "maxSpeed": 55,
        "accel": 3.2,
        "decel": 5.0,
        "sigma": 0.20,
        "tau": 0.7,
        "speedFactor": 1.15,
        "speedDev": 0.15,
        "description": "Taxis",
    },

    "truck_light": {
        "id": "truck_light",
        "vClass": "truck",
        "length": 7.5,
        "minGap": 3.5,
        "maxSpeed": 45,
        "accel": 1.8,
        "decel": 3.5,
        "sigma": 0.10,
        "tau": 1.2,
        "speedFactor": 0.9,
        # no speedDev -> will use default
        "description": "Light delivery trucks",
        "max_weight": 3500,
    },

    "truck_heavy": {
        "id": "truck_heavy",
        "vClass": "truck",
        "length": 10.0,
        "minGap": 4.0,
        "maxSpeed": 40,
        "accel": 1.3,
        "decel": 3.0,
        "sigma": 0.08,
        "tau": 1.3,
        "speedFactor": 0.8,
        # no speedDev -> will use default
        "description": "Heavy trucks",
        "max_weight": 40000,
    },

    "motorcycle": {
        "id": "motorcycle",
        "vClass": "motorcycle",
        "length": 2.0,
        "minGap": 1.5,
        "maxSpeed": 60,
        "accel": 4.0,
        "decel": 6.0,
        "sigma": 0.30,
        "tau": 0.5,
        "speedFactor": 1.3,
        "speedDev": 0.25,
        "description": "Motorcycles",
        "percentage_of_traffic": 0.05,
    },
}

# ============================================================================
# PART 3: SPEED RESTRICTIONS BY ZONE
# ============================================================================

SPEED_RESTRICTIONS = {
    "TAZ1_ResidentialNorth": 30,
    "TAZ2_ResidentialSouth": 30,
    "TAZ3_CommercialCenter": 40,
    "TAZ4_PortArea": 35,
    "TAZ5_IndustrialWest": 40,
    "TAZ6_Airport": 50,
    "TAZ7_University": 30,
    "TAZ8_BusinessDistrict": 40,
    "ART_RouteNationale": 50,
}

# ============================================================================
# PART 4: O-D MATRIX (PEAK HOUR 08:00-09:00)
# ============================================================================

OD_MATRIX_PEAK = {
    "TAZ1_ResidentialNorth": {
        "TAZ3_CommercialCenter": 150,
        "TAZ8_BusinessDistrict": 80,
        "TAZ4_PortArea": 50,
        "TAZ5_IndustrialWest": 40,
    },
    "TAZ2_ResidentialSouth": {
        "TAZ3_CommercialCenter": 120,
        "TAZ8_BusinessDistrict": 70,
        "TAZ4_PortArea": 60,
        "TAZ6_Airport": 30,
    },
    "TAZ3_CommercialCenter": {
        "TAZ1_ResidentialNorth": 100,
        "TAZ2_ResidentialSouth": 90,
        "TAZ4_PortArea": 110,
        "TAZ5_IndustrialWest": 60,
    },
    "TAZ4_PortArea": {
        "TAZ3_CommercialCenter": 80,
        "TAZ5_IndustrialWest": 150,
        "TAZ8_BusinessDistrict": 50,
    },
    "TAZ5_IndustrialWest": {
        "TAZ4_PortArea": 120,
        "TAZ3_CommercialCenter": 60,
    },
    "TAZ6_Airport": {
        "TAZ3_CommercialCenter": 50,
        "TAZ1_ResidentialNorth": 40,
    },
    "TAZ7_University": {
        "TAZ1_ResidentialNorth": 30,
        "TAZ2_ResidentialSouth": 35,
        "TAZ3_CommercialCenter": 25,
    },
    "TAZ8_BusinessDistrict": {
        "TAZ3_CommercialCenter": 70,
        "TAZ1_ResidentialNorth": 60,
        "TAZ4_PortArea": 40,
    },
}

# ============================================================================
# FUNCTIONS: GENERATE XML / JSON FILES
# ============================================================================

def generate_taz_xml():
    """Generate TAZ XML file"""
    root = ET.Element("additional")

    for taz_id, taz_info in TAZS.items():
        taz = ET.SubElement(root, "taz")
        taz.set("id", taz_id)
        taz.set("x", str(taz_info["centroid_lon"]))
        taz.set("y", str(taz_info["centroid_lat"]))
        taz.set("color", "255,0,0")

    tree = ET.ElementTree(root)
    tree.write("routetunis_tazs.xml", encoding="utf-8", xml_declaration=True)
    print("✓ Generated routetunis_tazs.xml")


def generate_vehicle_types_xml():
    """Generate vehicle types XML file"""
    root = ET.Element("additional")

    for vtype_id, vtype_info in VEHICLE_TYPES.items():
        vtype = ET.SubElement(root, "vType")
        vtype.set("id", vtype_info["id"])
        vtype.set("vClass", vtype_info["vClass"])
        vtype.set("length", str(vtype_info["length"]))
        vtype.set("minGap", str(vtype_info["minGap"]))
        vtype.set("maxSpeed", str(vtype_info["maxSpeed"]))
        vtype.set("accel", str(vtype_info["accel"]))
        vtype.set("decel", str(vtype_info["decel"]))
        vtype.set("sigma", str(vtype_info["sigma"]))
        vtype.set("tau", str(vtype_info["tau"]))
        vtype.set("speedFactor", str(vtype_info["speedFactor"]))
        # robust: default 0.1 if speedDev is missing
        speed_dev = vtype_info.get("speedDev", 0.1)
        vtype.set("speedDev", str(speed_dev))

    tree = ET.ElementTree(root)
    tree.write("routetunis_vehicle_types.xml", encoding="utf-8", xml_declaration=True)
    print("✓ Generated routetunis_vehicle_types.xml")


def generate_od_matrix_xml():
    """Generate O-D matrix XML file (SUMO format)"""
    root = ET.Element("demand")
    root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")

    # Vehicle types in OD file
    for vtype_id, vtype_info in VEHICLE_TYPES.items():
        vtype = ET.SubElement(root, "vType")
        vtype.set("id", vtype_info["id"])
        vtype.set("accel", str(vtype_info["accel"]))
        vtype.set("decel", str(vtype_info["decel"]))
        vtype.set("sigma", str(vtype_info["sigma"]))
        vtype.set("maxSpeed", str(vtype_info["maxSpeed"]))
        vtype.set("length", str(vtype_info["length"]))
        vtype.set("minGap", str(vtype_info["minGap"]))

    # Peak hour interval 08:00–09:00
    interval = ET.SubElement(root, "interval")
    interval.set("begin", "28800")
    interval.set("end", "32400")
    interval.set("id", "peak_hour")

    for origin, destinations in OD_MATRIX_PEAK.items():
        for destination, volume in destinations.items():
            od = ET.SubElement(interval, "od")
            od.set("from", origin)
            od.set("to", destination)
            od.set("count", str(volume))

    tree = ET.ElementTree(root)
    tree.write("routetunis_od_matrix.xml", encoding="utf-8", xml_declaration=True)
    print("✓ Generated routetunis_od_matrix.xml")


def generate_summary_json():
    """Generate JSON summary of the model"""
    summary = {
        "project": "Digital Twin - Route de Tunis",
        "date": datetime.now().isoformat(),
        "tazs": TAZS,
        "vehicle_types": VEHICLE_TYPES,
        "speed_restrictions": SPEED_RESTRICTIONS,
        "od_matrix_peak": OD_MATRIX_PEAK,
        "statistics": {
            "total_tazs": len(TAZS),
            "total_vehicle_types": len(VEHICLE_TYPES),
            "peak_hour_total_trips": sum(sum(d.values()) for d in OD_MATRIX_PEAK.values()),
        },
    }

    with open("routetunis_model_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("✓ Generated routetunis_model_summary.json")


def print_summary():
    """Print short console summary"""
    print("\n" + "=" * 80)
    print("DIGITAL TWIN FRAMEWORK - ROUTE DE TUNIS")
    print("=" * 80)

    total_trips = sum(sum(d.values()) for d in OD_MATRIX_PEAK.values())
    print(f"\nTAZs: {len(TAZS)}")
    print(f"Vehicle types: {len(VEHICLE_TYPES)}")
    print(f"Peak hour demand (08:00–09:00): {total_trips} vehicles")
    print("\n" + "=" * 80 + "\n")

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("\n🔧 BUILDING DIGITAL TWIN FOR ROUTE DE TUNIS\n")
    print("Generating files...")
    generate_taz_xml()
    generate_vehicle_types_xml()
    generate_od_matrix_xml()
    generate_summary_json()
    print_summary()
