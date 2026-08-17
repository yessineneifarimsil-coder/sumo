from qgis.core import QgsProject, QgsVectorLayer, QgsField, QgsFeature, QgsGeometry
from qgis.PyQt.QtCore import QVariant

all_layers = QgsProject.instance().mapLayers()
print("Couches disponibles:")
for layer_id, layer in all_layers.items():
    print(f"  - {layer.name()} (type: {layer.type()})")

layer = None
for layer_id, l in all_layers.items():
    # On ne garde que les couches VECTORIELLES
    if l.type() == 0 and l.geometryType() == 1:  # 0 = vecteur, 1 = ligne
        print(f"\nCouche ligne trouvée: {l.name()}")
        layer = l
        break

if layer is None:
    print("Erreur: Aucune couche LIGNE trouvée. Il faut d'abord une couche lineaire pour la Route de Tunis.")
else:
    crs = layer.crs()
    milestone_layer = QgsVectorLayer(f"Point?crs={crs.authid()}", "Distance_Markers", "memory")
    provider = milestone_layer.dataProvider()
    provider.addAttributes([QgsField("Distance_km", QVariant.Int)])
    milestone_layer.updateFields()
    
    features = []
    geometry = layer.getFeature(0).geometry()
    length = int(geometry.length())
    
    print(f"Longueur de la ligne: {length} m ({length/1000:.1f} km)")
    
    for distance in range(0, length, 1000):
        point = geometry.interpolate(distance).asPoint()
        feature = QgsFeature()
        feature.setGeometry(QgsGeometry.fromPointXY(point))
        feature.setAttributes([distance // 1000])
        features.append(feature)
    
    provider.addFeatures(features)
    QgsProject.instance().addMapLayer(milestone_layer)
    print(f"✓ Créé {len(features)} points de distance")
