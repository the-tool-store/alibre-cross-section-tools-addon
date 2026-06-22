from __future__ import division
import clr
import System
from System.Runtime.InteropServices import Marshal
from AlibreScript.API import *
import math
import time
def printTraceBack():
    import traceback
    traceback.print_exc()
    return
def show_error(msg, title='Error', include_trace=False):
    try:
        from System.Windows.Forms import MessageBox
        MessageBox.Show(str(msg), str(title), 
                       System.Windows.Forms.MessageBoxButtons.OK, 
                       System.Windows.Forms.MessageBoxIcon.Error)
    except:
        pass
    if include_trace:
        printTraceBack()
def show_info(msg, title='Info'):
    try:
        from System.Windows.Forms import MessageBox
        MessageBox.Show(str(msg), str(title), 
                       System.Windows.Forms.MessageBoxButtons.OK, 
                       System.Windows.Forms.MessageBoxIcon.Information)
    except:
        pass
def safe_try(fn):
    def _inner(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as ex:
            show_error('Unexpected error: %s' % ex, 'Unexpected Error', include_trace=True)
            return None
    return _inner
alibre = None
root = None
MyPart = None
try:
    alibre = Marshal.GetActiveObject("AlibreX.AutomationHook")
    root = alibre.Root
except Exception as ex:
    show_error('Could not connect to Alibre Automation. Details: %s' % ex, 
               'Alibre Connection Error', include_trace=True)
try:
    if root is not None:
        MyPart = Part(root.TopmostSession)
    else:
        MyPart = None
except Exception as ex:
    show_error('Could not get current Part session. Open a part and try again.\nDetails: %s' % ex, 
               'Part Error', include_trace=True)
    MyPart = None
try:
    clr.AddReference('System.Windows.Forms')
    clr.AddReference('System.Drawing')
except Exception as ex:
    show_error('Failed to load Windows Forms assemblies. Details: %s' % ex, 
               'Reference Load Error', include_trace=True)
from System.Windows.Forms import (
    ListBox, SelectionMode, Padding, AutoScaleMode,
    Timer, Button, ToolTip,
    DockStyle, Cursors, FlatStyle,
    Form, Label, CheckBox,
    MessageBox, Panel, TableLayoutPanel,
    TextBox, ScrollBars
)
from System.Drawing import Color, Size, SizeF, Font, FontStyle, SystemFonts
VERTEX_TOLERANCE = 1e-6
class PolygonProperties:
    def __init__(self, vertices_2d):
        self.vertices = vertices_2d
        self.n = len(vertices_2d)
        if self.n < 3:
            raise ValueError("Polygon must have at least 3 vertices")
        self._compute_properties()
    def _compute_properties(self):
        verts = self.vertices
        n = self.n
        signed_area = 0.0
        for i in range(n):
            j = (i + 1) % n
            signed_area += verts[i][0] * verts[j][1]
            signed_area -= verts[j][0] * verts[i][1]
        signed_area *= 0.5
        self.signed_area = signed_area
        self.area = abs(signed_area)
        if self.area < 1e-12:
            raise ValueError("Polygon has zero or negligible area")
        cx = 0.0
        cy = 0.0
        for i in range(n):
            j = (i + 1) % n
            cross = verts[i][0] * verts[j][1] - verts[j][0] * verts[i][1]
            cx += (verts[i][0] + verts[j][0]) * cross
            cy += (verts[i][1] + verts[j][1]) * cross
        factor = 1.0 / (6.0 * signed_area)
        self.centroid_x = cx * factor
        self.centroid_y = cy * factor
        Ix_origin = 0.0
        Iy_origin = 0.0
        Ixy_origin = 0.0
        for i in range(n):
            j = (i + 1) % n
            x0, y0 = verts[i]
            x1, y1 = verts[j]
            cross = x0 * y1 - x1 * y0
            Ix_origin += (y0*y0 + y0*y1 + y1*y1) * cross
            Iy_origin += (x0*x0 + x0*x1 + x1*x1) * cross
            Ixy_origin += (x0*y1 + 2*x0*y0 + 2*x1*y1 + x1*y0) * cross
        Ix_origin /= 12.0
        Iy_origin /= 12.0
        Ixy_origin /= 24.0
        self.Ix_origin = abs(Ix_origin)
        self.Iy_origin = abs(Iy_origin)
        self.Ixy_origin = -Ixy_origin if signed_area < 0 else Ixy_origin
        cx = self.centroid_x
        cy = self.centroid_y
        A = self.area
        self.Ix_centroid = abs(self.Ix_origin - A * cy * cy)
        self.Iy_centroid = abs(self.Iy_origin - A * cx * cx)
        self.Ixy_centroid = self.Ixy_origin - A * cx * cy
        self.J_centroid = self.Ix_centroid + self.Iy_centroid
        self._compute_principal_moments()
        self.rx = math.sqrt(self.Ix_centroid / A) if self.Ix_centroid > 0 else 0.0
        self.ry = math.sqrt(self.Iy_centroid / A) if self.Iy_centroid > 0 else 0.0
        self.rp = math.sqrt(self.J_centroid / A) if self.J_centroid > 0 else 0.0
        self._compute_bounding_box()
        self._compute_section_moduli()
    def _compute_principal_moments(self):
        Ix = self.Ix_centroid
        Iy = self.Iy_centroid
        Ixy = self.Ixy_centroid
        I_avg = (Ix + Iy) / 2.0
        I_diff = (Ix - Iy) / 2.0
        R = math.sqrt(I_diff * I_diff + Ixy * Ixy)
        self.I_max = max(0.0, I_avg + R)
        self.I_min = max(0.0, I_avg - R)
        if abs(Ixy) < 1e-12 and abs(I_diff) < 1e-12:
            self.theta_principal = 0.0
        else:
            self.theta_principal = 0.5 * math.atan2(-2.0 * Ixy, Ix - Iy)
        self.theta_principal_deg = math.degrees(self.theta_principal)
    def _compute_bounding_box(self):
        cx = self.centroid_x
        cy = self.centroid_y
        x_coords = [v[0] - cx for v in self.vertices]
        y_coords = [v[1] - cy for v in self.vertices]
        self.x_min = min(x_coords)
        self.x_max = max(x_coords)
        self.y_min = min(y_coords)
        self.y_max = max(y_coords)
        self.c_top = self.y_max
        self.c_bottom = abs(self.y_min)
        self.c_right = self.x_max
        self.c_left = abs(self.x_min)
    def _compute_section_moduli(self):
        self.Sx_top = self.Ix_centroid / self.c_top if self.c_top > 1e-12 else float('inf')
        self.Sx_bottom = self.Ix_centroid / self.c_bottom if self.c_bottom > 1e-12 else float('inf')
        self.Sy_right = self.Iy_centroid / self.c_right if self.c_right > 1e-12 else float('inf')
        self.Sy_left = self.Iy_centroid / self.c_left if self.c_left > 1e-12 else float('inf')
        self.Sx_min = min(self.Sx_top, self.Sx_bottom)
        self.Sy_min = min(self.Sy_right, self.Sy_left)
def vec3_subtract(a, b):
    return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]
def vec3_cross(a, b):
    return [a[1]*b[2] - a[2]*b[1], a[2]*b[0] - a[0]*b[2], a[0]*b[1] - a[1]*b[0]]
def vec3_dot(a, b):
    return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]
def vec3_length(v):
    return math.sqrt(v[0]*v[0] + v[1]*v[1] + v[2]*v[2])
def vec3_normalize(v):
    length = vec3_length(v)
    if length < 1e-12:
        return [0.0, 0.0, 0.0]
    return [v[0]/length, v[1]/length, v[2]/length]
def points_equal_3d(p1, p2, tol=VERTEX_TOLERANCE):
    return (abs(p1[0] - p2[0]) < tol and 
            abs(p1[1] - p2[1]) < tol and 
            abs(p1[2] - p2[2]) < tol)
def get_face_plane_basis(vertices_3d):
    if len(vertices_3d) < 3:
        raise ValueError("Need at least 3 vertices")
    n = len(vertices_3d)
    origin = [sum(v[0] for v in vertices_3d) / n,
              sum(v[1] for v in vertices_3d) / n,
              sum(v[2] for v in vertices_3d) / n]
    p0 = vertices_3d[0]
    p1 = None
    for i in range(1, n):
        if not points_equal_3d(vertices_3d[i], p0):
            p1 = vertices_3d[i]
            break
    if p1 is None:
        raise ValueError("All vertices are coincident")
    v1 = vec3_subtract(p1, p0)
    p2 = None
    for i in range(2, n):
        v2 = vec3_subtract(vertices_3d[i], p0)
        cross = vec3_cross(v1, v2)
        if vec3_length(cross) > 1e-9:
            p2 = vertices_3d[i]
            break
    if p2 is None:
        raise ValueError("All vertices are collinear")
    v2 = vec3_subtract(p2, p0)
    normal = vec3_normalize(vec3_cross(v1, v2))
    u_axis = vec3_normalize(v1)
    v_axis = vec3_cross(normal, u_axis)
    return origin, u_axis, v_axis, normal
def project_to_2d(vertices_3d, origin, u_axis, v_axis):
    vertices_2d = []
    for v3d in vertices_3d:
        rel = vec3_subtract(v3d, origin)
        u = vec3_dot(rel, u_axis)
        v = vec3_dot(rel, v_axis)
        vertices_2d.append([u, v])
    return vertices_2d
def order_vertices_by_angle(vertices_2d):
    # Order projected 2D points by angle about their centroid.
    # Mirrors the ordering approach used in adding-more-geometry-types.py's
    # project_to_2d. Note: angular sort is imperfect for concave polygons;
    # this is a known limitation but matches file 1 for consistency.
    n = len(vertices_2d)
    if n < 3:
        return vertices_2d
    cx = sum(p[0] for p in vertices_2d) / n
    cy = sum(p[1] for p in vertices_2d) / n
    def angle_key(p):
        return math.atan2(p[1] - cy, p[0] - cx)
    return sorted(vertices_2d, key=angle_key)
def remove_duplicate_vertices(vertices_2d, tol=VERTEX_TOLERANCE):
    if len(vertices_2d) < 2:
        return vertices_2d
    result = [vertices_2d[0]]
    for i in range(1, len(vertices_2d)):
        prev = result[-1]
        curr = vertices_2d[i]
        if abs(curr[0] - prev[0]) > tol or abs(curr[1] - prev[1]) > tol:
            result.append(curr)
    if len(result) > 1:
        if abs(result[-1][0] - result[0][0]) < tol and abs(result[-1][1] - result[0][1]) < tol:
            result = result[:-1]
    return result
def extract_ordered_boundary_from_edges(face):
    try:
        edges = face.GetEdges()
        if not edges or len(edges) == 0:
            return None
    except:
        return None
    edge_segments = []
    has_curved_edge = False
    for edge in edges:
        # Detect curved edges (arcs/circles) so we don't silently treat them
        # as straight chords. The AlibreScript edge API exposed in these
        # scripts only provides GetVertices()/Diameter/Length -- there is no
        # method to sample intermediate points along a curve -- so a curved
        # edge can only be approximated by the points GetVertices() returns.
        try:
            diam = edge.Diameter
            if diam is not None and diam > 0:
                has_curved_edge = True
        except:
            pass
        try:
            verts = edge.GetVertices()
            if not verts:
                continue
            # Use ALL vertices the edge exposes, in order, rather than only
            # the first two. If a curved edge ever returns intermediate sample
            # points they will be included; if it only returns endpoints, this
            # degrades gracefully to the original chord behavior.
            pts = [[v.X, v.Y, v.Z] for v in verts]
            if len(pts) >= 2:
                for k in range(len(pts) - 1):
                    edge_segments.append((pts[k], pts[k + 1]))
        except:
            continue
    if not edge_segments:
        return None
    # A curved boundary (circle/arc) that only exposed endpoints is
    # approximated as straight chords here. The annulus/circle analytical
    # paths do not exist in this file, so this chord approximation is the
    # safest available behavior; accuracy for curved faces is limited.
    _ = has_curved_edge
    boundary = [edge_segments[0][0], edge_segments[0][1]]
    used = [False] * len(edge_segments)
    used[0] = True
    max_iterations = len(edge_segments) * 2
    iterations = 0
    while iterations < max_iterations:
        iterations += 1
        current_end = boundary[-1]
        found = False
        for i in range(len(edge_segments)):
            if used[i]:
                continue
            v1, v2 = edge_segments[i]
            if points_equal_3d(v1, current_end):
                boundary.append(v2)
                used[i] = True
                found = True
                break
            elif points_equal_3d(v2, current_end):
                boundary.append(v1)
                used[i] = True
                found = True
                break
        if not found:
            break
        if points_equal_3d(boundary[-1], boundary[0]) and len(boundary) > 3:
            boundary = boundary[:-1]
            break
    return boundary if len(boundary) >= 3 else None
def extract_face_vertices_simple(face):
    vertices_3d = []
    try:
        vertex_objs = face.GetVertices()
        if vertex_objs:
            for v in vertex_objs:
                vertices_3d.append([v.X, v.Y, v.Z])
    except:
        pass
    return vertices_3d
def extract_face_boundary(face):
    # Returns (vertices_3d, is_ordered). is_ordered is True when the boundary
    # came from the edge-walk (already in sequential boundary order) and False
    # when it came from the unordered face-vertex fallback.
    boundary = extract_ordered_boundary_from_edges(face)
    if boundary and len(boundary) >= 3:
        return boundary, True
    return extract_face_vertices_simple(face), False
def get_unit_name():
    try:
        if Units.Current == UnitTypes.Inches:
            return "in"
        elif Units.Current == UnitTypes.Centimeters:
            return "cm"
        elif Units.Current == UnitTypes.Meters:
            return "m"
        elif Units.Current == UnitTypes.Feet:
            return "ft"
        else:
            return "mm"
    except:
        return "mm"
def get_face_alibre_area(face):
    try:
        return face.GetArea()
    except:
        return None
def format_number(value, decimals=6):
    if value is None:
        return "N/A"
    if abs(value) < 1e-10:
        return "0.0"
    elif abs(value) >= 1e6:
        return "%.3e" % value
    elif abs(value) < 0.001:
        return "%.3e" % value
    else:
        fmt = "%%.%df" % decimals
        return fmt % value
def generate_report(props, face_name, units, alibre_area=None):
    unit_area = units + "^2"
    unit_inertia = units + "^4"
    unit_modulus = units + "^3"
    lines = []
    lines.append("=" * 55)
    lines.append("     AREA MOMENTS OF INERTIA REPORT")
    lines.append("=" * 55)
    lines.append("")
    lines.append("Face: %s" % face_name)
    lines.append("Units: %s" % units)
    lines.append("Vertices: %d" % props.n)
    lines.append("")
    if alibre_area is not None:
        lines.append("-" * 55)
        lines.append("AREA VALIDATION")
        lines.append("-" * 55)
        lines.append("Calculated: %s %s" % (format_number(props.area, 6), unit_area))
        lines.append("Alibre:     %s %s" % (format_number(alibre_area, 6), unit_area))
        pct_diff = abs(props.area - alibre_area) / alibre_area * 100 if alibre_area > 0 else 0
        lines.append("Difference: %.4f%%" % pct_diff)
        lines.append("")
    lines.append("-" * 55)
    lines.append("BASIC PROPERTIES")
    lines.append("-" * 55)
    lines.append("Area:       %s %s" % (format_number(props.area, 6), unit_area))
    lines.append("Centroid X: %s %s" % (format_number(props.centroid_x, 6), units))
    lines.append("Centroid Y: %s %s" % (format_number(props.centroid_y, 6), units))
    lines.append("")
    lines.append("-" * 55)
    lines.append("MOMENTS OF INERTIA (Centroidal)")
    lines.append("-" * 55)
    lines.append("Ix:   %s %s" % (format_number(props.Ix_centroid, 6), unit_inertia))
    lines.append("Iy:   %s %s" % (format_number(props.Iy_centroid, 6), unit_inertia))
    lines.append("Ixy:  %s %s" % (format_number(props.Ixy_centroid, 6), unit_inertia))
    lines.append("J:    %s %s" % (format_number(props.J_centroid, 6), unit_inertia))
    lines.append("")
    lines.append("-" * 55)
    lines.append("PRINCIPAL MOMENTS")
    lines.append("-" * 55)
    lines.append("I_max: %s %s" % (format_number(props.I_max, 6), unit_inertia))
    lines.append("I_min: %s %s" % (format_number(props.I_min, 6), unit_inertia))
    lines.append("Angle: %s deg" % format_number(props.theta_principal_deg, 4))
    lines.append("")
    lines.append("-" * 55)
    lines.append("RADII OF GYRATION")
    lines.append("-" * 55)
    lines.append("rx: %s %s" % (format_number(props.rx, 6), units))
    lines.append("ry: %s %s" % (format_number(props.ry, 6), units))
    lines.append("rp: %s %s" % (format_number(props.rp, 6), units))
    lines.append("")
    lines.append("-" * 55)
    lines.append("SECTION MODULI")
    lines.append("-" * 55)
    lines.append("Sx_min: %s %s" % (format_number(props.Sx_min, 6), unit_modulus))
    lines.append("Sy_min: %s %s" % (format_number(props.Sy_min, 6), unit_modulus))
    lines.append("")
    lines.append("=" * 55)
    return System.Environment.NewLine.join(lines)
def calculate_face_properties(face):
    face_name = "Selected Face"
    try:
        face_name = str(face.Name)
    except:
        pass
    vertices_3d, is_ordered = extract_face_boundary(face)
    if vertices_3d is None or len(vertices_3d) < 3:
        raise ValueError("Could not extract face boundary")
    origin, u_axis, v_axis, normal = get_face_plane_basis(vertices_3d)
    vertices_2d = project_to_2d(vertices_3d, origin, u_axis, v_axis)
    if not is_ordered:
        # Fallback vertices come back in arbitrary order; order them by angle
        # about their centroid (same approach as adding-more-geometry-types.py)
        # before the shoelace polygon math so area/centroid/inertia are correct.
        vertices_2d = order_vertices_by_angle(vertices_2d)
    vertices_2d = remove_duplicate_vertices(vertices_2d)
    if len(vertices_2d) < 3:
        raise ValueError("Face has fewer than 3 unique vertices")
    props = PolygonProperties(vertices_2d)
    unit_name = get_unit_name()
    alibre_area = get_face_alibre_area(face)
    report = generate_report(props, face_name, unit_name, alibre_area)
    return props, report
def get_professional_colors():
    return {
        'background': Color.FromArgb(250, 250, 250),
        'accent': Color.FromArgb(0, 122, 204),
        'accent_light': Color.FromArgb(230, 244, 255),
        'border': Color.FromArgb(204, 204, 204),
        'text': Color.FromArgb(64, 64, 64),
        'button_bg': Color.FromArgb(240, 240, 240)
    }
def create_professional_button(text, is_primary=False):
    colors = get_professional_colors()
    btn = Button()
    btn.Text = text
    btn.FlatStyle = FlatStyle.Flat
    btn.Font = Font(SystemFonts.DefaultFont.FontFamily, 9, FontStyle.Regular)
    btn.UseVisualStyleBackColor = False
    if is_primary:
        btn.BackColor = colors['accent']
        btn.ForeColor = Color.White
        btn.FlatAppearance.BorderColor = colors['accent']
    else:
        btn.BackColor = colors['button_bg']
        btn.ForeColor = colors['text']
        btn.FlatAppearance.BorderColor = colors['border']
    btn.FlatAppearance.BorderSize = 1
    btn.Cursor = Cursors.Hand
    return btn
def create_professional_label(text, is_header=False):
    colors = get_professional_colors()
    lbl = Label()
    lbl.Text = text
    lbl.ForeColor = colors['text']
    lbl.AutoSize = True
    lbl.TextAlign = System.Drawing.ContentAlignment.TopLeft
    lbl.Font = Font(SystemFonts.DefaultFont.FontFamily, 10 if is_header else 9,
                    FontStyle.Bold if is_header else FontStyle.Regular)
    return lbl
def create_professional_checkbox(text):
    colors = get_professional_colors()
    chk = CheckBox()
    chk.Text = text
    chk.ForeColor = colors['text']
    chk.Font = Font(SystemFonts.DefaultFont.FontFamily, 9)
    chk.UseVisualStyleBackColor = True
    chk.AutoSize = True
    chk.TextAlign = System.Drawing.ContentAlignment.MiddleLeft
    return chk
class SelectionListBox(ListBox):
    def __new__(cls):
        instance = ListBox.__new__(cls)
        try:
            instance.AutoScaleDimensions = SizeF(96, 96)
            instance.AutoScaleMode = AutoScaleMode.Dpi
            instance.IntegralHeight = 1
            instance.SelectionMode = SelectionMode.MultiExtended
            instance.BackColor = Color.White
            instance.BorderStyle = System.Windows.Forms.BorderStyle.FixedSingle
            instance.Font = Font(SystemFonts.DefaultFont.FontFamily, 9)
            import AlibreScript
            Root = AlibreScript.API.Global.Root
            instance.Root = Root
            instance.top_sess = instance.Root.TopmostSession
            instance.myTimer = Timer()
            instance.myTimer.Tick += instance.TimerEventProcessor
            instance.myTimer.Interval = 100
            instance.Enter += instance.onEnter_Selection
            instance.Leave += instance.onLeave_Selection
            instance.HandleDestroyed += instance.onHandleDestroyed
            instance.PreviousSelection = instance.Root.NewObjectCollector()
        except Exception as ex:
            show_error('Selection list init failed: %s' % ex, include_trace=True)
        return instance
    @safe_try
    def onEnter_Selection(self, sender, e):
        colors = get_professional_colors()
        sender.BackColor = colors['accent_light']
        sender.myTimer.Start()
    @safe_try
    def onLeave_Selection(self, sender, e):
        try:
            sender.myTimer.Stop()
        finally:
            sender.BackColor = Color.White
    @safe_try
    def onHandleDestroyed(self, sender, e):
        try:
            sender.myTimer.Stop()
        finally:
            pass
    @safe_try
    def TimerEventProcessor(self, sender, e):
        try:
            self.myTimer.Stop()
            if self.top_sess is None:
                return
            try:
                if self.PreviousSelection is None:
                    self.PreviousSelection = self.Root.NewObjectCollector()
            except:
                return
            NewSelections = getattr(self.top_sess, 'SelectedObjects', None)
            if NewSelections is None:
                return
            try:
                count = int(NewSelections.Count)
            except:
                return
            for a in range(0, count):
                item = NewSelections.Item(a)
                tgt = getattr(item, 'Target', None)
                if tgt is None:
                    continue
                tname = ''
                topo_type = ''
                try:
                    tname = str(tgt.Type)
                except:
                    try:
                        tname = str(tgt.GetType().Name)
                    except:
                        tname = ''
                is_face = False
                if 'AD_TOPOLOGY' in tname.upper():
                    try:
                        topo_type = str(tgt.TopologyType).upper()
                        if 'FACE' in topo_type:
                            is_face = True
                    except:
                        pass
                elif 'FACE' in tname.upper():
                    is_face = True
                if is_face:
                    try:
                        obj_name = str(item.DisplayName)
                    except:
                        obj_name = 'Face'
                    if self.Items.Count == 0 or obj_name != self.Items[0]:
                        self.Items.Clear()
                        try:
                            self.PreviousSelection.Clear()
                        except:
                            try:
                                self.PreviousSelection = self.Root.NewObjectCollector()
                            except:
                                pass
                        self.Items.Add(obj_name)
                        try:
                            self.PreviousSelection.Add(item)
                        except:
                            pass
                    break
        finally:
            try:
                self.myTimer.Start()
            except:
                pass
def show_area_moments_form():
    if MyPart is None:
        show_error('No active Part session was found. Open a part and run the script again.', 
                   'No Part Session')
        return None
    colors = get_professional_colors()
    form = Form()
    form.Text = 'Area Moments of Inertia'
    form.AutoSize = False
    form.StartPosition = System.Windows.Forms.FormStartPosition.CenterScreen
    form.FormBorderStyle = System.Windows.Forms.FormBorderStyle.Sizable
    form.MaximizeBox = True
    form.MinimizeBox = True
    form.ShowInTaskbar = True
    form.ShowIcon = False
    form.TopMost = True
    form.BackColor = colors['background']
    form.Font = Font(SystemFonts.DefaultFont.FontFamily, 9)
    form.Padding = Padding(12)
    main_panel = Panel()
    main_panel.Dock = DockStyle.Fill
    main_panel.BackColor = colors['background']
    main_panel.Padding = Padding(8)
    main_panel.AutoScroll = True
    form.Controls.Add(main_panel)
    table = TableLayoutPanel()
    table.ColumnCount = 1
    table.RowCount = 0
    table.Dock = DockStyle.Fill
    table.AutoSize = False
    table.Padding = Padding(0)
    table.Margin = Padding(0)
    table.ColumnStyles.Add(System.Windows.Forms.ColumnStyle(System.Windows.Forms.SizeType.Percent, 100.0))
    main_panel.Controls.Add(table)
    control_spacing = 8
    section_spacing = 16
    def add_control_row(ctrl, extra_margin_bottom=None, fixed_height=None, fill_remaining=False):
        table.RowCount += 1
        if fill_remaining:
            table.RowStyles.Add(System.Windows.Forms.RowStyle(System.Windows.Forms.SizeType.Percent, 100.0))
        elif fixed_height is not None:
            table.RowStyles.Add(System.Windows.Forms.RowStyle(System.Windows.Forms.SizeType.Absolute, fixed_height))
            ctrl.Height = fixed_height
        else:
            table.RowStyles.Add(System.Windows.Forms.RowStyle(System.Windows.Forms.SizeType.AutoSize))
        mb = control_spacing if extra_margin_bottom is None else extra_margin_bottom
        ctrl.Margin = Padding(0, 0, 0, mb)
        ctrl.Dock = DockStyle.Fill
        table.Controls.Add(ctrl, 0, table.RowCount - 1)
    add_control_row(create_professional_label("Area Moments of Inertia", True), 
                    extra_margin_bottom=section_spacing)
    add_control_row(create_professional_label("Face Selection", True), extra_margin_bottom=6)
    add_control_row(create_professional_label("Select a planar face to analyze:"))
    sel_face = SelectionListBox()
    sel_face.IntegralHeight = False
    sel_face.Height = 60
    add_control_row(sel_face, fixed_height=60, extra_margin_bottom=section_spacing)
    chk_stay_open = create_professional_checkbox("Stay open after calculating")
    add_control_row(chk_stay_open, extra_margin_bottom=section_spacing)
    add_control_row(create_professional_label("Results", True), extra_margin_bottom=6)
    txt_results = TextBox()
    txt_results.Multiline = True
    txt_results.ReadOnly = True
    txt_results.ScrollBars = ScrollBars.Both
    txt_results.Font = Font("Consolas", 9)
    txt_results.BackColor = Color.White
    txt_results.WordWrap = False
    txt_results.AcceptsReturn = True
    add_control_row(txt_results, fill_remaining=True, extra_margin_bottom=section_spacing)
    def close_form_safely():
        try:
            if hasattr(sel_face, 'myTimer') and sel_face.myTimer is not None:
                sel_face.myTimer.Stop()
                sel_face.myTimer.Dispose()
        except:
            pass
        try:
            form.Close()
            form.Dispose()
        except:
            pass
    def reset_tool_state():
        try:
            try:
                sel_face.Items.Clear()
            except:
                pass
            try:
                if getattr(sel_face, 'Root', None) is not None:
                    sel_face.PreviousSelection = sel_face.Root.NewObjectCollector()
                else:
                    sel_face.PreviousSelection = None
            except:
                sel_face.PreviousSelection = None
            try:
                sel_face.myTimer.Stop()
                sel_face.myTimer.Start()
            except:
                pass
            try:
                sel_face.Focus()
                form.Activate()
            except:
                pass
        except Exception as reset_ex:
            print('Reset warning: %s' % reset_ex)
    @safe_try
    def calculate_click(sender, e):
        try:
            if sel_face.Items.Count == 0 or sel_face.PreviousSelection is None:
                show_info("Please select a face", "Input Required")
                return
            selected_item = sel_face.PreviousSelection.Item(0)
            target = getattr(selected_item, 'Target', None)
            if target is None:
                show_error('Could not resolve the selected face.', 'Selection Error')
                return
            target_type = str(target.GetType().Name).upper()
            if 'FACE' not in target_type and 'TOPOLOGY' not in target_type:
                show_error('Please select a valid face. Selected type: %s' % target_type, 
                          'Invalid Selection')
                return
            try:
                face_display_name = str(selected_item.DisplayName)
                if ':' in face_display_name:
                    face_display_name = face_display_name.split(':')[-1].strip()
                proper_face = MyPart.GetFace(face_display_name)
            except Exception as face_ex:
                show_error('Could not get face object: %s\nDisplayName: %s' % (face_ex, face_display_name), 
                          'Face Access Error')
                return
            if proper_face is None:
                show_error('Face not found: %s' % face_display_name, 'Face Not Found')
                return
            try:
                props, report = calculate_face_properties(proper_face)
                txt_results.Text = report
                txt_results.SelectionStart = 0
                txt_results.ScrollToCaret()
                print("")
                print(report)
                if not chk_stay_open.Checked:
                    close_form_safely()
                else:
                    reset_tool_state()
            except Exception as calc_ex:
                show_error("Calculation failed: %s" % calc_ex, "Calculation Error", include_trace=True)
        except Exception as ex:
            show_error("Failed to calculate: %s" % ex, "Error", include_trace=True)
    def cancel_click(sender, e):
        close_form_safely()
    btn_calculate = create_professional_button("Calculate", True)
    btn_calculate.Dock = DockStyle.Fill
    add_control_row(btn_calculate, extra_margin_bottom=8, fixed_height=50)
    btn_close = create_professional_button("Close", False)
    btn_close.Dock = DockStyle.Fill
    add_control_row(btn_close, extra_margin_bottom=0, fixed_height=40)
    btn_calculate.Click += calculate_click
    btn_close.Click += safe_try(cancel_click)
    tooltip = ToolTip()
    tooltip.SetToolTip(sel_face, "Click here, then select a planar face in Alibre")
    tooltip.SetToolTip(chk_stay_open, "Leave window open after calculating")
    tooltip.SetToolTip(btn_calculate, "Calculate area moments of inertia")
    table.PerformLayout()
    main_panel.PerformLayout()
    try:
        form.ClientSize = Size(520, 650)
        form.MinimumSize = Size(400, 500)
    except Exception as ex:
        print('Form sizing warning: %s' % ex)
    try:
        form.Show()
    except Exception as ex:
        show_error('Failed to display form: %s' % ex, include_trace=True)
        return None
    return form
try:
    moments_form = show_area_moments_form()
except Exception as ex:
    show_error('Fatal error while creating the Area Moments UI: %s' % ex, include_trace=True)