from __future__ import division
import sys
import math
# Auto-import all AlibreScript classes (for VS Code autocomplete only)
from AlibreScript import *
ScriptVersion = "0"
DIALOG_WIDTH = 500
CURVE_SEGMENTS = 72
VERTEX_TOLERANCE = 1e-6
DECIMALS_STANDARD = 6
DECIMALS_COMPACT = 4
DECIMALS_ANGLE = 2
UNIT_OPTIONS = ['mm', 'cm', 'm', 'in', 'ft']
IDX_FACE = 0
IDX_UNITS = 1
ScriptName = "Dev"
class CircleProperties:
    """Analytical properties for a solid circular cross-section"""
    
    def __init__(self, radius, center_x=0.0, center_y=0.0):
        self.radius = radius
        self.n = 0
        
        r = radius
        A = math.pi * r * r
        I = math.pi * r**4 / 4.0
        
        self.area = A
        self.centroid_x = center_x
        self.centroid_y = center_y
        
        self.Ix_centroid = I
        self.Iy_centroid = I
        self.Ixy_centroid = 0.0
        self.J_centroid = 2 * I
        
        self.Ix_origin = I + A * center_y**2
        self.Iy_origin = I + A * center_x**2
        self.Ixy_origin = A * center_x * center_y
        
        self.I_max = I
        self.I_min = I
        self.theta_principal = 0.0
        self.theta_principal_deg = 0.0
        
        self.rx = r / 2.0
        self.ry = r / 2.0
        self.rp = r / math.sqrt(2.0)
        
        self.c_top = r
        self.c_bottom = r
        self.c_right = r
        self.c_left = r
        
        S = I / r
        self.Sx_top = S
        self.Sx_bottom = S
        self.Sy_right = S
        self.Sy_left = S
        self.Sx_min = S
        self.Sy_min = S


class AnnulusProperties:
    """Analytical properties for a ring/annular cross-section (hollow circle)"""
    
    def __init__(self, outer_radius, inner_radius, center_x=0.0, center_y=0.0):
        self.outer_radius = outer_radius
        self.inner_radius = inner_radius
        self.n = 0
        
        R = outer_radius  # Outer radius
        r = inner_radius  # Inner radius
        
        # Ensure R > r
        if R < r:
            R, r = r, R
        
        A = math.pi * (R**2 - r**2)
        I = math.pi * (R**4 - r**4) / 4.0
        
        self.area = A
        self.centroid_x = center_x
        self.centroid_y = center_y
        
        self.Ix_centroid = I
        self.Iy_centroid = I
        self.Ixy_centroid = 0.0
        self.J_centroid = 2 * I
        
        self.Ix_origin = I + A * center_y**2
        self.Iy_origin = I + A * center_x**2
        self.Ixy_origin = A * center_x * center_y
        
        self.I_max = I
        self.I_min = I
        self.theta_principal = 0.0
        self.theta_principal_deg = 0.0
        
        # Radii of gyration
        self.rx = math.sqrt(I / A)
        self.ry = math.sqrt(I / A)
        self.rp = math.sqrt(2 * I / A)
        
        # Bounding box (outer radius)
        self.c_top = R
        self.c_bottom = R
        self.c_right = R
        self.c_left = R
        
        # Section moduli (based on outer radius)
        S = I / R
        self.Sx_top = S
        self.Sx_bottom = S
        self.Sy_right = S
        self.Sy_left = S
        self.Sx_min = S
        self.Sy_min = S

class PolygonProperties:
    """Computes 2D area properties using Green's theorem"""
    
    def __init__(self, vertices_2d):
        self.vertices = vertices_2d
        self.n = len(vertices_2d)
        
        if self.n < 3:
            raise ValueError("Polygon must have at least 3 vertices")
        
        self._compute_all()
    
    def _compute_all(self):
        verts = self.vertices
        n = self.n
        
        # Signed area
        signed_area = 0.0
        for i in range(n):
            j = (i + 1) % n
            signed_area += verts[i][0] * verts[j][1]
            signed_area -= verts[j][0] * verts[i][1]
        signed_area *= 0.5
        
        self.area = abs(signed_area)
        if self.area < 1e-12:
            raise ValueError("Polygon has zero area")
        
        # Centroid
        cx, cy = 0.0, 0.0
        for i in range(n):
            j = (i + 1) % n
            cross = verts[i][0] * verts[j][1] - verts[j][0] * verts[i][1]
            cx += (verts[i][0] + verts[j][0]) * cross
            cy += (verts[i][1] + verts[j][1]) * cross
        
        factor = 1.0 / (6.0 * signed_area)
        self.centroid_x = cx * factor
        self.centroid_y = cy * factor
        
        # Second moments about origin
        Ix, Iy, Ixy = 0.0, 0.0, 0.0
        for i in range(n):
            j = (i + 1) % n
            x0, y0 = verts[i]
            x1, y1 = verts[j]
            cross = x0 * y1 - x1 * y0
            Ix += (y0*y0 + y0*y1 + y1*y1) * cross
            Iy += (x0*x0 + x0*x1 + x1*x1) * cross
            Ixy += (x0*y1 + 2*x0*y0 + 2*x1*y1 + x1*y0) * cross
        
        self.Ix_origin = abs(Ix / 12.0)
        self.Iy_origin = abs(Iy / 12.0)
        self.Ixy_origin = Ixy / 24.0 if signed_area > 0 else -Ixy / 24.0
        
        # Centroidal moments
        A = self.area
        self.Ix_centroid = abs(self.Ix_origin - A * self.centroid_y**2)
        self.Iy_centroid = abs(self.Iy_origin - A * self.centroid_x**2)
        self.Ixy_centroid = self.Ixy_origin - A * self.centroid_x * self.centroid_y
        self.J_centroid = self.Ix_centroid + self.Iy_centroid
        
        # Principal moments
        Ix_c, Iy_c, Ixy_c = self.Ix_centroid, self.Iy_centroid, self.Ixy_centroid
        I_avg = (Ix_c + Iy_c) / 2.0
        I_diff = (Ix_c - Iy_c) / 2.0
        R = math.sqrt(I_diff**2 + Ixy_c**2)
        
        self.I_max = I_avg + R
        self.I_min = max(0.0, I_avg - R)
        
        if abs(Ixy_c) < 1e-12 and abs(I_diff) < 1e-12:
            self.theta_principal = 0.0
        else:
            self.theta_principal = 0.5 * math.atan2(-2.0 * Ixy_c, Ix_c - Iy_c)
        self.theta_principal_deg = math.degrees(self.theta_principal)
        
        # Radii of gyration
        self.rx = math.sqrt(self.Ix_centroid / A)
        self.ry = math.sqrt(self.Iy_centroid / A)
        self.rp = math.sqrt(self.J_centroid / A)
        
        # Bounding box relative to centroid
        x_rel = [v[0] - self.centroid_x for v in verts]
        y_rel = [v[1] - self.centroid_y for v in verts]
        
        self.c_top = max(y_rel)
        self.c_bottom = abs(min(y_rel))
        self.c_right = max(x_rel)
        self.c_left = abs(min(x_rel))
        
        # Section moduli
        self.Sx_top = self.Ix_centroid / self.c_top if self.c_top > 1e-12 else float('inf')
        self.Sx_bottom = self.Ix_centroid / self.c_bottom if self.c_bottom > 1e-12 else float('inf')
        self.Sy_right = self.Iy_centroid / self.c_right if self.c_right > 1e-12 else float('inf')
        self.Sy_left = self.Iy_centroid / self.c_left if self.c_left > 1e-12 else float('inf')
        self.Sx_min = min(self.Sx_top, self.Sx_bottom)
        self.Sy_min = min(self.Sy_right, self.Sy_left)

def vec_subtract(a, b):
    return [a[0]-b[0], a[1]-b[1], a[2]-b[2]]

def vec_cross(a, b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]

def vec_dot(a, b):
    return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]

def vec_length(v):
    return math.sqrt(v[0]**2 + v[1]**2 + v[2]**2)

def vec_normalize(v):
    L = vec_length(v)
    return [v[0]/L, v[1]/L, v[2]/L] if L > 1e-12 else [0, 0, 0]

def vec_distance(a, b):
    return math.sqrt((b[0]-a[0])**2 + (b[1]-a[1])**2 + (b[2]-a[2])**2)
def analyze_face(face):
    """
    Analyze face to determine type and extract geometry.
    Returns: (face_type, properties, alibre_area)
    """
    # Get Alibre's area (may be 0 or None for some face types)
    alibre_area = None
    try:
        alibre_area = face.GetArea()
        if alibre_area == 0:
            alibre_area = None
    except:
        pass
    
    # Get edges and vertices
    edges = []
    try:
        edges = face.GetEdges() or []
    except:
        pass
    
    vertices = []
    try:
        vertices = face.GetVertices() or []
    except:
        pass  
    # Debug output
    print "=" * 60
    print "FACE ANALYSIS"
    print "=" * 60
    print "Alibre Area: %s" % alibre_area
    print "Number of edges: %d" % len(edges)
    print "Number of vertices: %d" % len(vertices)
    
    # Collect edge info
    edge_diameters = []
    edge_info = []
    
    for i, edge in enumerate(edges):
        info = {'index': i, 'vertices': 0, 'diameter': None, 'length': None}
        
        try:
            edge_verts = edge.GetVertices() or []
            info['vertices'] = len(edge_verts)
        except:
            pass
        
        try:
            diam = edge.Diameter
            if diam is not None and diam > 0:
                info['diameter'] = diam
                edge_diameters.append(diam)
        except:
            pass
        
        try:
            length = edge.Length
            info['length'] = length
        except:
            pass
        
        edge_info.append(info)
        print "Edge %d: verts=%s, diam=%s, len=%s" % (
            i, info['vertices'], info['diameter'], info['length'])
    
    print "-" * 60   
    # CASE 1: Ring/Annulus - Two edges both with diameters (concentric circles)
    if len(edge_diameters) == 2:
        d1, d2 = edge_diameters[0], edge_diameters[1]
        r1, r2 = d1 / 2.0, d2 / 2.0
        outer_r = max(r1, r2)
        inner_r = min(r1, r2)
        
        print "DETECTED: Annulus/Ring"
        print "  Outer radius: %s" % outer_r
        print "  Inner radius: %s" % inner_r
        
        props = AnnulusProperties(outer_r, inner_r)
        return ("annulus", props, props.area)
    
    # CASE 2: Solid Circle - One edge with diameter
    if len(edge_diameters) == 1:
        radius = edge_diameters[0] / 2.0
        
        print "DETECTED: Solid Circle"
        print "  Radius: %s" % radius
        
        props = CircleProperties(radius)
        return ("circle", props, props.area)
    
    # CASE 3: Multiple circular edges (like a tube cross-section with multiple rings)
    if len(edge_diameters) > 2:
        # Sort diameters and take outer/inner
        sorted_diams = sorted(edge_diameters, reverse=True)
        outer_r = sorted_diams[0] / 2.0
        inner_r = sorted_diams[-1] / 2.0
        
        if outer_r > inner_r:
            print "DETECTED: Multi-edge Annulus"
            print "  Outer radius: %s" % outer_r
            print "  Inner radius: %s" % inner_r
            
            props = AnnulusProperties(outer_r, inner_r)
            return ("annulus", props, props.area)
    
    # CASE 4: Polygon from vertices
    print "Attempting polygon extraction..."
    
    boundary_points = []
    
    # Collect unique points from edge vertices
    for edge in edges:
        try:
            edge_verts = edge.GetVertices()
            if edge_verts:
                for v in edge_verts:
                    pt = [v.X, v.Y, v.Z]
                    is_dup = False
                    for existing in boundary_points:
                        if vec_distance(pt, existing) < VERTEX_TOLERANCE:
                            is_dup = True
                            break
                    if not is_dup:
                        boundary_points.append(pt)
        except:
            pass 
    # Fallback to face vertices if needed
    if len(boundary_points) < 3:
        boundary_points = []
        for v in vertices:
            try:
                pt = [v.X, v.Y, v.Z]
                is_dup = False
                for existing in boundary_points:
                    if vec_distance(pt, existing) < VERTEX_TOLERANCE:
                        is_dup = True
                        break
                if not is_dup:
                    boundary_points.append(pt)
            except:
                pass 
    print "Extracted %d unique boundary points" % len(boundary_points)   
    if len(boundary_points) >= 3:
        return ("polygon", boundary_points, alibre_area)    
    # CASE 5: Fallback - if we have any diameter, use it as a circle
    if len(edge_diameters) > 0:
        # Use largest diameter as outer circle
        max_diam = max(edge_diameters)
        radius = max_diam / 2.0
        
        print "FALLBACK: Using largest diameter as circle"
        print "  Radius: %s" % radius
        
        props = CircleProperties(radius)
        return ("circle", props, props.area)
    
    # CASE 6: Ultimate fallback - derive from Alibre area if available
    if alibre_area and alibre_area > 0:
        radius = math.sqrt(alibre_area / math.pi)
        
        print "FALLBACK: Deriving circle from area"
        print "  Derived radius: %s" % radius
        
        props = CircleProperties(radius)
        return ("circle", props, alibre_area)
    
    return ("unknown", None, alibre_area)

def project_to_2d(points_3d):
    """Project 3D points to 2D plane and order for polygon"""
    n = len(points_3d)
    if n < 3:
        raise ValueError("Need at least 3 points")
    
    # Compute centroid
    cx = sum(p[0] for p in points_3d) / n
    cy = sum(p[1] for p in points_3d) / n
    cz = sum(p[2] for p in points_3d) / n
    origin = [cx, cy, cz]
    
    # Find plane basis
    p0 = points_3d[0]
    v1 = None
    
    for i in range(1, n):
        vec = vec_subtract(points_3d[i], p0)
        if vec_length(vec) > VERTEX_TOLERANCE:
            v1 = vec
            break
    
    if v1 is None:
        raise ValueError("All points coincident")
    
    # Find non-parallel vector
    v2 = None
    for i in range(2, n):
        vec = vec_subtract(points_3d[i], p0)
        cross = vec_cross(v1, vec)
        if vec_length(cross) > VERTEX_TOLERANCE:
            v2 = vec
            break
    
    if v2 is None:
        if abs(v1[2]) < 0.9:
            v2 = vec_cross(v1, [0, 0, 1])
        else:
            v2 = vec_cross(v1, [1, 0, 0])
    
    # Create orthonormal basis
    normal = vec_normalize(vec_cross(v1, v2))
    u_axis = vec_normalize(v1)
    v_axis = vec_cross(normal, u_axis)
    
    # Project points
    points_2d = []
    for p3d in points_3d:
        rel = vec_subtract(p3d, origin)
        u = vec_dot(rel, u_axis)
        v = vec_dot(rel, v_axis)
        points_2d.append([u, v])
    
    # Order by angle around centroid
    cx2 = sum(p[0] for p in points_2d) / n
    cy2 = sum(p[1] for p in points_2d) / n
    
    def angle_key(p):
        return math.atan2(p[1] - cy2, p[0] - cx2)
    
    points_2d.sort(key=angle_key)
    
    return points_2d

def fmt(value, decimals=6):
    if value is None:
        return "N/A"
    if abs(value) < 1e-10:
        return "0.0"
    elif abs(value) >= 1e6 or abs(value) < 0.001:
        return "%.3e" % value
    else:
        return ("%%.%df" % decimals) % value
def generate_report(props, face_name, face_type, units, alibre_area):
    """Generate full console report"""
    u = units
    u2 = units + "^2"
    u4 = units + "^4"
    u3 = units + "^3"
    p = props
    
    lines = []
    lines.append("")
    lines.append("=" * 70)
    lines.append("            AREA MOMENTS OF INERTIA REPORT")
    lines.append("            %s v%s" % (ScriptName, ScriptVersion))
    lines.append("=" * 70)
    lines.append("")
    lines.append("Face: %s" % face_name)
    lines.append("Type: %s" % face_type)
    lines.append("Units: %s" % u)
    
    # Show radii for circles/annuli
    if hasattr(props, 'radius'):
        lines.append("Radius: %s %s" % (fmt(props.radius), u))
    if hasattr(props, 'outer_radius'):
        lines.append("Outer Radius: %s %s" % (fmt(props.outer_radius), u))
        lines.append("Inner Radius: %s %s" % (fmt(props.inner_radius), u))
    
    lines.append("")
    
    if alibre_area and alibre_area > 0:
        lines.append("-" * 70)
        lines.append("VALIDATION")
        lines.append("-" * 70)
        lines.append("  Calculated Area: %s %s" % (fmt(p.area), u2))
        lines.append("  Alibre Area:     %s %s" % (fmt(alibre_area), u2))
        diff = abs(p.area - alibre_area) / alibre_area * 100
        lines.append("  Difference:      %.2f%%" % diff)
        lines.append("")
    
    lines.append("-" * 70)
    lines.append("BASIC PROPERTIES")
    lines.append("-" * 70)
    lines.append("  Area:            %s %s" % (fmt(p.area), u2))
    lines.append("  Centroid X:      %s %s" % (fmt(p.centroid_x), u))
    lines.append("  Centroid Y:      %s %s" % (fmt(p.centroid_y), u))
    lines.append("")
    
    lines.append("-" * 70)
    lines.append("SECOND MOMENTS (Centroidal)")
    lines.append("-" * 70)
    lines.append("  Ix:              %s %s" % (fmt(p.Ix_centroid), u4))
    lines.append("  Iy:              %s %s" % (fmt(p.Iy_centroid), u4))
    lines.append("  Ixy:             %s %s" % (fmt(p.Ixy_centroid), u4))
    lines.append("  J (polar):       %s %s" % (fmt(p.J_centroid), u4))
    lines.append("")
    
    lines.append("-" * 70)
    lines.append("PRINCIPAL MOMENTS")
    lines.append("-" * 70)
    lines.append("  I_max:           %s %s" % (fmt(p.I_max), u4))
    lines.append("  I_min:           %s %s" % (fmt(p.I_min), u4))
    lines.append("  Angle:           %s deg" % fmt(p.theta_principal_deg, 2))
    lines.append("")
    
    lines.append("-" * 70)
    lines.append("RADII OF GYRATION")
    lines.append("-" * 70)
    lines.append("  rx:              %s %s" % (fmt(p.rx), u))
    lines.append("  ry:              %s %s" % (fmt(p.ry), u))
    lines.append("  rp:              %s %s" % (fmt(p.rp), u))
    lines.append("")
    
    lines.append("-" * 70)
    lines.append("SECTION MODULI")
    lines.append("-" * 70)
    lines.append("  Sx (min):        %s %s" % (fmt(p.Sx_min), u3))
    lines.append("  Sy (min):        %s %s" % (fmt(p.Sy_min), u3))
    lines.append("")
    
    lines.append("-" * 70)
    lines.append("EXTREME FIBER DISTANCES")
    lines.append("-" * 70)
    lines.append("  c_top:           %s %s" % (fmt(p.c_top), u))
    lines.append("  c_bottom:        %s %s" % (fmt(p.c_bottom), u))
    lines.append("  c_right:         %s %s" % (fmt(p.c_right), u))
    lines.append("  c_left:          %s %s" % (fmt(p.c_left), u))
    lines.append("")
    
    lines.append("=" * 70)
    
    return "\n".join(lines)
def get_current_unit():
    try:
        if Units.Current == UnitTypes.Inches:
            return "in"
        elif Units.Current == UnitTypes.Centimeters:
            return "cm"
        elif Units.Current == UnitTypes.Meters:
            return "m"
        elif Units.Current == UnitTypes.Feet:
            return "ft"
    except:
        pass
    return "mm"
class AreaMomentsApp:
    
    def __init__(self):
        self.Win = None
    
    def check_part(self):
        try:
            p = CurrentPart()
            return p is not None
        except:
            return False
    
    def calculate(self, values):
        face = values[IDX_FACE]
        unit_idx = values[IDX_UNITS]
        units = UNIT_OPTIONS[unit_idx]
        
        if face is None:
            self.Win.ErrorDialog("Please select a planar face.", ScriptName)
            return
        
        try:
            # Get face name
            face_name = "Selected Face"
            try:
                if hasattr(face, 'Name') and face.Name:
                    face_name = str(face.Name)
            except:
                pass
            
            # Analyze face
            face_type, data, alibre_area = analyze_face(face)
            
            if face_type == "circle":
                props = data
                type_str = "Circle (analytical)"
            
            elif face_type == "annulus":
                props = data
                type_str = "Annulus/Ring (analytical)"
            
            elif face_type == "polygon":
                points_2d = project_to_2d(data)
                props = PolygonProperties(points_2d)
                type_str = "Polygon (%d pts)" % len(points_2d)
            
            else:
                self.Win.ErrorDialog(
                    "Could not determine face geometry.\n\n"
                    "The face may not be planar or may have unsupported geometry.",
                    ScriptName
                )
                return
            
            # Generate and print report
            report = generate_report(props, face_name, type_str, units, alibre_area)
            print report
        
        except ValueError as ex:
            self.Win.ErrorDialog("Calculation Error:\n%s" % str(ex), ScriptName)
        except Exception as ex:
            self.Win.ErrorDialog("Error:\n%s\n\nType: %s" % (str(ex), type(ex).__name__), ScriptName)  
    def on_change(self, idx, val):
        pass   
    def run(self):
        if not self.check_part():
            Win = Windows()
            Win.ErrorDialog("Please open a part before running this script.", ScriptName)
            return
        
        self.Win = Windows()      
        curr_unit = get_current_unit()
        try:
            default_idx = UNIT_OPTIONS.index(curr_unit)
        except:
            default_idx = 0        
        Options = []
        Options.append(['Select Planar Face', WindowsInputTypes.Face, None])
        Options.append(['Output Units', WindowsInputTypes.StringList, UNIT_OPTIONS, UNIT_OPTIONS[default_idx]])
        self.Win.UtilityDialog(
            ScriptName + " v" + ScriptVersion,
            'Calculate',
            self.calculate,
            self.on_change,
            Options,
            DIALOG_WIDTH
        )
app = AreaMomentsApp()
app.run()
