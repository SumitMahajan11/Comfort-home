#!/usr/bin/env python3
"""
Convert official Survey of India (SOI) GeoJSON boundary from Datameet into
an optimized, lightweight SVG path for IndiaClimateMap.tsx with exact lat/lon projection.
"""

import json
import math

def rdp(points, epsilon):
    """Ramer-Douglas-Peucker polygon simplification."""
    if len(points) < 3:
        return points

    dmax = 0.0
    index = 0
    end = len(points) - 1

    x1, y1 = points[0]
    x2, y2 = points[end]
    dx = x2 - x1
    dy = y2 - y1
    denom = math.hypot(dx, dy)

    for i in range(1, end):
        x0, y0 = points[i]
        if denom == 0:
            d = math.hypot(x0 - x1, y0 - y1)
        else:
            d = abs(dy * x0 - dx * y0 + x2 * y1 - y2 * x1) / denom
        if d > dmax:
            index = i
            dmax = d

    if dmax > epsilon:
        rec1 = rdp(points[:index + 1], epsilon)
        rec2 = rdp(points[index:], epsilon)
        return rec1[:-1] + rec2
    else:
        return [points[0], points[end]]

def albers_projection(lon, lat):
    """
    Albers Equal-Area Conic projection for India.
    Standard parallels: 12°N, 28°N. Central meridian: 82.5°E. Latitude of origin: 20°N.
    """
    phi1 = math.radians(12.0)
    phi2 = math.radians(28.0)
    phi0 = math.radians(20.0)
    lambda0 = math.radians(82.5)

    n = 0.5 * (math.sin(phi1) + math.sin(phi2))
    c = math.cos(phi1)**2 + 2 * n * math.sin(phi1)
    rho0 = math.sqrt(c - 2 * n * math.sin(phi0)) / n

    phi = math.radians(lat)
    lam = math.radians(lon)

    theta = n * (lam - lambda0)
    term = c - 2 * n * math.sin(phi)
    if term < 0:
        term = 0
    rho = math.sqrt(term) / n

    x = rho * math.sin(theta)
    y = rho0 - rho * math.cos(theta)
    return x, y

def main():
    with open("web/src/data/india-soi.geojson", "r") as f:
        data = json.load(f)

    geom = data["features"][0]["geometry"]
    coords = geom["coordinates"]

    # Filter out tiny island rings with very few points, simplify main rings
    # Bounding box in projected coordinates
    all_proj = []
    simplified_rings = []

    # tolerance in degrees
    epsilon = 0.04

    for poly in coords:
        for ring in poly:
            if len(ring) < 10:
                continue
            simp = rdp(ring, epsilon)
            if len(simp) < 4:
                continue
            proj_ring = [albers_projection(lon, lat) for lon, lat in simp]
            all_proj.extend(proj_ring)
            simplified_rings.append(proj_ring)

    min_x = min(p[0] for p in all_proj)
    max_x = max(p[0] for p in all_proj)
    min_y = min(p[1] for p in all_proj)
    max_y = max(p[1] for p in all_proj)

    width = 600
    height = 680
    padding = 24

    scale_x = (width - 2 * padding) / (max_x - min_x)
    scale_y = (height - 2 * padding) / (max_y - min_y)
    scale = min(scale_x, scale_y)

    cx = (min_x + max_x) / 2
    cy = (min_y + max_y) / 2

    def to_svg(x, y):
        svg_x = (x - cx) * scale + width / 2
        # Inverted y for SVG (y increases downwards)
        svg_y = (cy - y) * scale + height / 2
        return round(svg_x, 1), round(svg_y, 1)

    svg_paths = []
    for ring in simplified_rings:
        pts = [to_svg(x, y) for x, y in ring]
        path_str = f"M {pts[0][0]},{pts[0][1]} " + " ".join(f"L {p[0]},{p[1]}" for p in pts[1:]) + " Z"
        svg_paths.append(path_str)

    # 5 station coordinates from EPW
    stations = {
        "Shimla": (77.167, 31.100),
        "New_Delhi": (77.103, 28.567),
        "Jodhpur": (73.041, 26.257),
        "Mumbai": (72.868, 19.089),
        "Bengaluru": (77.668, 12.950)
    }

    station_svg = {}
    for name, (lon, lat) in stations.items():
        px, py = albers_projection(lon, lat)
        sx, sy = to_svg(px, py)
        station_svg[name] = {"x": sx, "y": sy, "lat": lat, "lon": lon}

    print("Projected station positions:")
    for k, v in station_svg.items():
        print(f"  {k}: x={v['x']}, y={v['y']}")

    full_svg_d = " ".join(svg_paths)
    print(f"\nGenerated SVG path length: {len(full_svg_d)} chars, {len(svg_paths)} subpaths")

    # Output to a json file for easy import into component
    out = {
        "source": "Survey of India (SOI) official external boundary (via Datameet Community Maps, ODbL)",
        "viewBox": f"0 0 {width} {height}",
        "path": full_svg_d,
        "stations": station_svg,
        "projectionParams": {
            "scale": scale,
            "cx": cx,
            "cy": cy,
            "width": width,
            "height": height
        }
    }

    with open("web/src/data/india_map_soi.json", "w") as f:
        json.dump(out, f, indent=2)

    print("Saved output to web/src/data/india_map_soi.json")

if __name__ == "__main__":
    main()
