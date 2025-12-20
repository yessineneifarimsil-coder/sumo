#!/usr/bin/env python3
"""
Define traffic signals and roundabouts for Route de Tunis
This script documents and programmatically validates traffic control infrastructure.
"""

import xml.etree.ElementTree as ET

# Traffic control infrastructure inventory
TRAFFIC_SIGNALS = {
    "INT1_RueMoise": {
        "node_id": -3115,
        "cross_street": "Rue de Moïse",
        "phase_green_duration": 30,      # seconds
        "phase_red_duration": 30,        # seconds
        "offset": 0,                     # seconds (for coordination)
        "location_description": "Intersection of Rue de Moïse and Route de Tunis"
    },
    "INT2_AvenueElBoustene": {
        "node_id": -3121,
        "cross_street": "Avenue El Boustène",
        "phase_green_duration": 32,
        "phase_red_duration": 32,
        "offset": 10,                    # Offset for green wave
        "location_description": "Commercial district access"
    },
    "INT3_AvenueHedrChaker": {
        "node_id": -5174,
        "cross_street": "Avenue Hédi Chaker",
        "phase_green_duration": 28,
        "phase_red_duration": 28,
        "offset": 20,                    # Offset for green wave
        "location_description": "Residential zone distribution"
    }
}

ROUNDABOUTS = {
    "RB1_BoulevardBizerte": {
        "node_id": -836,
        "connecting_streets": ["Boulevard de Bizerte", "Boulevard Majida Boulila", "Route de Tunis"],
        "priority_rule": "vehicles_in_roundabout_have_priority",
        "lanes": 2,
        "location_description": "Boulevard de Bizerte junction"
    },
    "RB2_RouteBizerteSplit": {
        "node_id": -3156,
        "connecting_streets": ["Route de Bizerte", "Route de Tunis", "Route de Tanniour"],
        "priority_rule": "vehicles_in_roundabout_have_priority",
        "lanes": 2,
        "type": "major_distribution_hub",
        "location_description": "Route de Bizerte splits into Route de Tunis and Route de Tanniour"
    },
    "RB3_CeintureBourguiba": {
        "node_id": -3194,
        "connecting_streets": ["Ceinture Bourguiba", "Route de Tunis"],
        "priority_rule": "vehicles_in_roundabout_have_priority",
        "lanes": 2,
        "location_description": "Bourguiba Ring Road connection"
    },
    "RB4_ElOns": {
        "node_id": -3185,
        "connecting_streets": ["Local streets", "Route de Tunis"],
        "priority_rule": "vehicles_in_roundabout_have_priority",
        "lanes": 2,
        "location_description": "El Ons / El Sedra junction"
    }
}

ARTERIAL_SEGMENTS = {
    "ART_RouteNationale": {
        "name": "Route Nationale Tunis - Ras Jedir",
        "common_name": "Route de Tunis",
        "length_km": 13,
        "lanes": 3,  # 2-3 lanes per direction (bidirectional)
        "speed_limit_kmh": 50,
        "type": "urban_arterial",
        "description": "Main corridor connecting residential zones (North) to commercial/port zones (South)"
    }
}

def print_infrastructure_summary():
    """Print summary of all traffic control infrastructure"""
    
    print("\n" + "="*70)
    print("ROUTE DE TUNIS - TRAFFIC CONTROL INFRASTRUCTURE INVENTORY")
    print("="*70)
    
    print(f"\n{'TRAFFIC SIGNALS':^70}")
    print("-"*70)
    for name, info in TRAFFIC_SIGNALS.items():
        print(f"\n{name}")
        print(f"  Node ID: {info['node_id']}")
        print(f"  Cross Street: {info['cross_street']}")
        print(f"  Green Duration: {info['phase_green_duration']}s")
        print(f"  Red Duration: {info['phase_red_duration']}s")
        print(f"  Offset: {info['offset']}s (for signal coordination)")
        print(f"  Location: {info['location_description']}")
    
    print(f"\n\n{'ROUNDABOUTS':^70}")
    print("-"*70)
    for name, info in ROUNDABOUTS.items():
        print(f"\n{name}")
        print(f"  Node ID: {info['node_id']}")
        print(f"  Connecting Streets: {', '.join(info['connecting_streets'])}")
        print(f"  Priority Rule: {info['priority_rule']}")
        print(f"  Lanes: {info['lanes']}")
        print(f"  Location: {info['location_description']}")
    
    print(f"\n\n{'ARTERIAL SEGMENT':^70}")
    print("-"*70)
    for name, info in ARTERIAL_SEGMENTS.items():
        print(f"\n{name}")
        print(f"  Official Name: {info['name']}")
        print(f"  Common Name: {info['common_name']}")
        print(f"  Length: {info['length_km']} km")
        print(f"  Lanes: {info['lanes']} per direction (bidirectional)")
        print(f"  Speed Limit: {info['speed_limit_kmh']} km/h")
        print(f"  Description: {info['description']}")
    
    print("\n" + "="*70)
    print(f"TOTAL: {len(TRAFFIC_SIGNALS)} signals + {len(ROUNDABOUTS)} roundabouts + 1 arterial")
    print("="*70 + "\n")

def export_to_json():
    """Export infrastructure data to JSON for documentation"""
    import json
    
    infrastructure_data = {
        "route_name": "Route Nationale Tunis - Ras Jedir",
        "corridor_name": "Route de Tunis",
        "length_km": 13,
        "traffic_signals": TRAFFIC_SIGNALS,
        "roundabouts": ROUNDABOUTS,
        "arterial_segments": ARTERIAL_SEGMENTS
    }
    
    with open("route_de_tunis_infrastructure.json", "w", encoding="utf-8") as f:
        json.dump(infrastructure_data, f, indent=2, ensure_ascii=False)
    
    print("✓ Exported route_de_tunis_infrastructure.json")

def export_to_csv():
    """Export infrastructure summary to CSV for reference"""
    import csv
    
    # Signals CSV
    with open("traffic_signals_inventory.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["ID", "Node_ID", "Cross_Street", "Green_Duration_s", "Red_Duration_s", "Offset_s", "Location"])
        writer.writeheader()
        for name, info in TRAFFIC_SIGNALS.items():
            writer.writerow({
                "ID": name,
                "Node_ID": info["node_id"],
                "Cross_Street": info["cross_street"],
                "Green_Duration_s": info["phase_green_duration"],
                "Red_Duration_s": info["phase_red_duration"],
                "Offset_s": info["offset"],
                "Location": info["location_description"]
            })
    
    print("✓ Exported traffic_signals_inventory.csv")
    
    # Roundabouts CSV
    with open("roundabouts_inventory.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["ID", "Node_ID", "Connecting_Streets", "Lanes", "Location"])
        writer.writeheader()
        for name, info in ROUNDABOUTS.items():
            writer.writerow({
                "ID": name,
                "Node_ID": info["node_id"],
                "Connecting_Streets": "; ".join(info["connecting_streets"]),
                "Lanes": info["lanes"],
                "Location": info["location_description"]
            })
    
    print("✓ Exported roundabouts_inventory.csv")

def generate_thesis_markdown():
    """Generate markdown documentation for thesis"""
    
    md_content = """# Route de Tunis Infrastructure Specification

## Overview
Route de Tunis (Route Nationale Tunis - Ras Jedir) is a 13 km urban arterial corridor in Sfax, Tunisia.

## Traffic Signals

"""
    
    for name, info in TRAFFIC_SIGNALS.items():
        md_content += f"""### {name}
- **Node ID:** {info['node_id']}
- **Cross Street:** {info['cross_street']}
- **Signal Timing:** Green {info['phase_green_duration']}s, Red {info['phase_red_duration']}s
- **Coordination Offset:** {info['offset']}s
- **Location:** {info['location_description']}

"""
    
    md_content += "\n## Roundabouts\n\n"
    
    for name, info in ROUNDABOUTS.items():
        md_content += f"""### {name}
- **Node ID:** {info['node_id']}
- **Connecting Streets:** {', '.join(info['connecting_streets'])}
- **Lanes:** {info['lanes']}
- **Location:** {info['location_description']}

"""
    
    with open("infrastructure_specification.md", "w", encoding="utf-8") as f:
        f.write(md_content)
    
    print("✓ Exported infrastructure_specification.md")

if __name__ == "__main__":
    print("\n📍 Route de Tunis Traffic Control Infrastructure Documentation\n")
    
    # Print summary
    print_infrastructure_summary()
    
    # Export to multiple formats
    print("\n📁 Exporting documentation...")
    export_to_json()
    export_to_csv()
    generate_thesis_markdown()
    
    print("\n✓ Documentation complete!")
    print("\nFiles created:")
    print("  - route_de_tunis_infrastructure.json")
    print("  - traffic_signals_inventory.csv")
    print("  - roundabouts_inventory.csv")
    print("  - infrastructure_specification.md")
