# Alibre Cross-Section Tools Add-On

An Alibre Design add-on that computes section properties for a selected planar face of a part. Select a face, calculate, and read back area, centroid, moments of inertia, and related cross-section data.

## Features
- Computes area, centroid, and centroidal moments of inertia (Ix, Iy, Ixy, J) for a selected planar face.
- Reports principal moments (I_max, I_min) and the principal axis angle.
- Reports radii of gyration (rx, ry, rp) and minimum section moduli (Sx, Sy).
- Validates the computed area against Alibre's reported face area and shows the percentage difference.
- Interactive Windows Forms dialog with live face selection and a formatted, copyable results report.
- Results are shown in the current document's units (in, cm, m, ft, or mm).

## Requirements
- Alibre Design 29.0.0.29060 with the AlibreScript add-on.
- .NET Framework 4.8.1 (x64).
- IronPython 2.7 runtime (bundled in the add-on output; `IronPython.dll` and supporting assemblies ship alongside the add-on DLL).

## Installation
Install via the provided installer (built from `source/alibre-cross-section-tools-addon.iss`), which deploys the add-on to `Program Files\Alibre Design Add-Ons\alibre-cross-section-tools-addon` and registers it with Alibre Design.

To install manually, copy the contents of `source/bin/Release/net481` (the add-on DLL, the `.adc` manifest, the IronPython assemblies, and the `scripts` folder) to a folder, then register that folder under the `HKLM\SOFTWARE\Alibre Design Add-Ons` registry key using the add-on name. The `.adc` manifest registers the add-on and its menu with Alibre Design at startup.

## Usage
1. Open a part in Alibre Design.
2. Launch the **alibre-cross-section-tools-addon** command from the add-on menu to open the Area Moments of Inertia dialog.
3. Click the face-selection box, then pick a planar face in the model.
4. Click **Calculate** to display the section-properties report. Enable **Stay open after calculating** to analyze multiple faces without reopening the dialog.

## License
See [LICENSE](../LICENSE).
