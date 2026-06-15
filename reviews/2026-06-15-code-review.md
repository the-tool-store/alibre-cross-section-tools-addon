# Code Review — alibre-cross-section-tools-addon

- **Date:** 2026-06-15
- **Branch:** `review/2026-06-15-code-review` (branched from `main` @ `1ea1940` — "Add script name variable to geometry types script")
- **Reviewer:** Claude (Opus 4.8)
- **Scope:** Full repository review (VB.NET add-on host + IronPython cross-section scripts + Inno Setup installer + project file)

---

## 1. Summary

This is an Alibre Design add-on that adds a ribbon command which runs an IronPython script
(`scripts/Template.py`) to compute area moments of inertia (area, centroid, second moments,
principal moments, radii of gyration, section moduli) for a user-selected planar face. The host
is VB.NET (`AlibreAddOn.vb`, `alibre-cross-section-tools-addon.vbproj`); the modeling/analysis
logic and WinForms UI live in the Python scripts. `scripts/alibre_setup.py` is a bootstrap loaded
before the main script.

The repo is small (1 VB source file, 3 Python scripts, plus a `.adc` manifest, `.iss` installer,
project file, license, README, and screenshots). The host plumbing is notably *better* than the
sibling `alibre-shapes-addon`: the Alibre install path is resolved **dynamically at runtime**
(not hard-coded), and the session lookup in `InvokeCommand` is defensive. However, the **Inno
Setup script is hard-wired to a developer's `D:\` machine paths** and will not build for anyone
else, the **`.adc` and project file reference files that do not exist** (`logo.ico`,
`AlibreScriptAddon.adc`), the **csproj carries a phantom copy-paste reference**, and the
self-described "PoC/pre-alpha" scripts have real defects: `Template.py` ignores the session the
host injects and re-acquires `TopmostSession`, and the third script
(`adding-more-geometry-types.py`) is **never wired to any menu command** (dead in the add-on) and
contains a call-vs-variable bug.

**Overall:** Working proof-of-concept with a broken/unportable installer and copy-paste project
cruft, but a cleaner C#/VB host layer than its sibling. Fix the installer paths and the dangling
file references before shipping; the math itself looks sound.

### Findings by severity

| Severity | Count |
|----------|-------|
| Critical | 1 |
| High     | 4 |
| Medium   | 4 |
| Low / Nit| 6 |

---

## 2. Critical

### C-1. Installer is hard-wired to a developer's `D:\` machine and will not build/package anywhere else
**File:** [alibre-cross-section-tools-addon.iss:9,35,37](../alibre-cross-section-tools-addon.iss)

```pascal
#define MyOutputDir "D:\AlibreExtensions\source\Working\Projects\alibre-cross-section-tools-addon\bin\Release\net481"
...
Source: "{#MyOutputDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "D:\AlibreExtensions\source\Working\Projects\alibre-cross-section-tools-addon\alibre-cross-section-tools-addon.adc"; DestDir: "{app}"; ...
```

Both the build-output directory and the `.adc` source are absolute paths under
`D:\AlibreExtensions\source\Working\Projects\...` — a path that exists only on the original
author's machine and is *not even inside this repository* (the repo lives elsewhere and has no
`source\Working` tree). On any clone, the Inno Setup compile fails immediately with "source file
not found". Make these relative to the `.iss` location, e.g.:

```pascal
#define MyOutputDir "bin\Release\net481"
...
Source: "{#MyOutputDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "alibre-cross-section-tools-addon.adc"; DestDir: "{app}"; Flags: ignoreversion
```

(Inno resolves relative `Source:` paths against `SourceDir`, which defaults to the script's own
directory.) This is the single blocking issue for producing a release.

---

## 3. High

### H-1. `.adc` manifest points at `logo.ico`, but only `logo.png` exists and no icon is ever copied
**Files:** [alibre-cross-section-tools-addon.adc:5](../alibre-cross-section-tools-addon.adc), [alibre-cross-section-tools-addon.vbproj:23](../alibre-cross-section-tools-addon.vbproj)

```xml
<Icon location="logo.ico"/>
```

`git ls-files` shows the repo contains `logo.png` but **no `logo.ico`** (verified: `find . -iname
"*.ico"` returns nothing). The project file even has `<None Remove="logo.ico" />`
([vbproj:23](../alibre-cross-section-tools-addon.vbproj)) referencing the same missing file, and
**no `<Content Include>` ever copies any icon to the output directory**. So at runtime Alibre
will look for `logo.ico` next to the DLL and not find it. Either add a real `logo.ico`, copy it to
output, and keep the manifest — or point the manifest at an icon that actually ships. (The sibling
review flagged the inverse problem; here the icon is simply missing.)

### H-2. `Template.py` ignores the session the host injected and re-acquires `TopmostSession`
**Files:** [scripts/Template.py:42-49](../scripts/Template.py) vs [scripts/alibre_setup.py:6-11](../scripts/alibre_setup.py) and [AlibreAddOn.vb:103-111](../AlibreAddOn.vb)

`AlibreAddOn.vb` carefully resolves the invoked `session`, injects it as `CurrentSession`, and
runs `alibre_setup.py`, which builds `CurrentPart` from exactly that session:

```python
# alibre_setup.py
if CurrentSession and isinstance(CurrentSession, AlibreX.IADPartSession):
    CurrentPart = Part(CurrentSession)
```

But `Template.py` throws all of that away and re-connects from scratch:

```python
alibre = Marshal.GetActiveObject("AlibreX.AutomationHook")
root = alibre.Root
...
MyPart = Part(root.TopmostSession)   # not necessarily the invoked session
```

`TopmostSession` is whatever window happens to be frontmost, which may not be the document the
ribbon command was invoked on, so the analyzed face can be resolved against the wrong part. It
also makes `alibre_setup.py`'s `CurrentSession`/`CurrentPart` plumbing entirely dead. Use the
`CurrentPart` that setup already prepared.

### H-3. Phantom copy-paste `Reference` in the project file
**File:** [alibre-cross-section-tools-addon.vbproj:46-49](../alibre-cross-section-tools-addon.vbproj)

```xml
<Reference Include="alibre-cross-section-tools-addon">
  <HintPath>C:\Program Files\Alibre Design 28.1.1.28227\Program\Addons\AlibreScript\AlibreScriptAddOn.dll</HintPath>
  <Private>False</Private>
</Reference>
```

The reference is *named* `alibre-cross-section-tools-addon` (this project itself) but its
`HintPath` points at Alibre's `AlibreScriptAddOn.dll`. This is a copy-paste artifact: either it is
meant to be a reference named `AlibreScriptAddOn` (the assembly the Python scripts import via
`clr.AddReference('AlibreScriptAddOn')`), or it is redundant. As written, the assembly identity
and the file on disk disagree, which is confusing at best and can produce a self-referential or
misnamed reference at build time. Rename it to `AlibreScriptAddOn` (matching the DLL) or remove it
if the runtime `clr.AddReference` is sufficient.

### H-4. Project file copies a non-existent `.adc` and references a non-existent `icons\` tree
**File:** [alibre-cross-section-tools-addon.vbproj:15-24,56-58](../alibre-cross-section-tools-addon.vbproj)

```xml
<ItemGroup>
  <Compile Remove="icons\**" />        <!-- no icons\ directory exists -->
  ...
</ItemGroup>
...
<None Update="AlibreScriptAddon.adc">  <!-- no such file in the repo -->
  <CopyToOutputDirectory>Always</CopyToOutputDirectory>
</None>
```

There is no `icons\` directory and no `AlibreScriptAddon.adc` (the real manifest is
`alibre-cross-section-tools-addon.adc`, already handled at
[vbproj:26-28](../alibre-cross-section-tools-addon.vbproj)). The `<None Update>` on a missing file
is a no-op that signals the project was cloned from another add-on and never cleaned. Remove the
`icons\**` blocks and the stray `AlibreScriptAddon.adc` item.

---

## 4. Medium

### M-1. Installer's Alibre-detection registry key is wrong
**File:** [alibre-cross-section-tools-addon.iss:51](../alibre-cross-section-tools-addon.iss)

```pascal
if not RegKeyExists(HKEY_LOCAL_MACHINE, 'SOFTWARE\Alibre, Inc.\Alibre Design') then
```

Alibre Design registers itself under `SOFTWARE\Alibre, LLC\...` (the company is Alibre, **LLC**),
not "Alibre, Inc." This check will therefore (almost) always fail and prompt every user with the
"Alibre does not appear to be installed" dialog even when it is installed. Confirm the actual key
on a target machine and correct it (or drop the optional check).

### M-2. `adding-more-geometry-types.py` is dead code in the add-on and has a call-vs-variable bug
**Files:** [AlibreAddOn.vb:71-74](../AlibreAddOn.vb), [scripts/adding-more-geometry-types.py:586-591](../scripts/adding-more-geometry-types.py)

`InvokeCommand` only ever runs `Template.py`:

```vbnet
Select Case menuId
    Case CMD
        runner.ExecuteScript(session, Path.Combine(scriptsPath, "Template.py"))
End Select
```

so `adding-more-geometry-types.py` can never be triggered through the add-on UI. It is also not
copied to the output directory by the `.vbproj` (only `alibre_setup.py` and `Template.py` are at
[vbproj:29-34](../alibre-cross-section-tools-addon.vbproj)). On top of being unreachable, it has a
bug:

```python
def check_part(self):
    try:
        p = CurrentPart()   # CurrentPart is a variable (None or a Part), not a callable
        return p is not None
    except:
        return False
```

`alibre_setup.py` defines `CurrentPart` as a *value* (a `Part` instance or `None`), so
`CurrentPart()` either raises `TypeError: 'NoneType' object is not callable` or calls the `Part`
instance — both wrong. Because it is wrapped in a bare `except`, `check_part` silently always
returns `False`, so even if wired up the script would always claim "Please open a part." Decide
whether this script is in-scope: either wire it to a menu id + copy it to output + fix
`CurrentPart()` → `CurrentPart`, or remove it from the repo.

### M-3. `print` statements unconditionally `print` to a console that an add-on usually has none of
**Files:** [scripts/adding-more-geometry-types.py:264-300,637](../scripts/adding-more-geometry-types.py), [scripts/Template.py:701-702](../scripts/Template.py)

Both scripts call `print(...)` for diagnostics and even the final report
(`print report`). When the script is run by the embedded IronPython engine inside Alibre (no
attached stdout), these either go nowhere or can raise. `Template.py` does also surface the report
in the WinForms `txt_results` textbox (good), but the `print` calls are redundant/fragile. Route
diagnostics through the existing `show_info`/`show_error` helpers, or guard prints, rather than
relying on a console.

### M-4. Generic, duplicated menu text / tooltip strings
**File:** [AlibreAddOn.vb:127-143](../AlibreAddOn.vb)

Every `MenuItemText` and `MenuItemToolTip` case returns the bare add-on id string
`"alibre-cross-section-tools-addon"` for both the root and the command. Users see the repo slug
instead of a human label like "Cross-Section Tools" / "Area Moments of Inertia…". Give the root
and command meaningful, distinct text and a descriptive tooltip.

---

## 5. Low / Nits

### L-1. Hard-coded, version-pinned `HintPath`s in the project file
[alibre-cross-section-tools-addon.vbproj:43,47,51](../alibre-cross-section-tools-addon.vbproj):
all three `<Reference>` `HintPath`s pin `C:\Program Files\Alibre Design 28.1.1.28227\...`. This
only matters at *build* time (the runtime path is resolved dynamically — see "What looks good"),
but it still breaks the build on any other Alibre version / install location. Consider an MSBuild
property (`$(AlibreInstallDir)`) resolved from the registry or an env var.

### L-2. `RootNamespace` is empty
[alibre-cross-section-tools-addon.vbproj:4](../alibre-cross-section-tools-addon.vbproj):
`<RootNamespace></RootNamespace>` is blank. It happens to work because the code declares
`Namespace AlibreAddOnAssembly` explicitly, but an empty root namespace is unusual — set it
explicitly (e.g. `AlibreAddOnAssembly`) or remove the element.

### L-3. Unused / version-mismatched `ScriptVersion` and unused imports
[scripts/adding-more-geometry-types.py:6,16](../scripts/adding-more-geometry-types.py):
`ScriptVersion = "0"` and `ScriptName = "Dev"` produce a report header of "Dev v0", and
`import sys` ([line 2](../scripts/adding-more-geometry-types.py)) is unused. In
[scripts/Template.py:7](../scripts/Template.py) `import time` is never used. Minor cleanup.

### L-4. `Template.py` brittle face-name parsing
[scripts/Template.py:684-695](../scripts/Template.py): the selected face is resolved by string-
munging the WinForms `DisplayName` (`split(':')[-1].strip()`) and feeding it to
`MyPart.GetFace(name)`. This depends on Alibre's display-name formatting and on the name being
unique; a geometry-based lookup or using the selected `Target` object directly would be more
robust. The README itself notes "circular faces aren't working," which is consistent with this
fragile path.

### L-5. Installer version (`1.0.0`) disagrees with the project's stated maturity
[alibre-cross-section-tools-addon.iss:6](../alibre-cross-section-tools-addon.iss) sets
`MyAppVersion "1.0.0"` while the README ([README.md:23](../README.md)) and the GitHub release tag
describe this as "PoC/pre-alpha". Pick a single, honest version scheme (e.g. `0.1.0-pre`) so the
installer, README, and release tags agree.

### L-6. Binary screenshots committed at repo root
`git ls-files` shows `A.png`, `B.png`, `SNAG-0013.png`, `SNAG-0014.png`, and `logo.png` tracked at
the repo root. Only `SNAG-0013/0014.png` and `logo.png` are referenced (README / manifest); `A.png`
and `B.png` appear unused. Move docs images under a `docs/`/`images/` folder and drop the orphans
to keep the root tidy.

---

## 6. What looks good

- **Dynamic Alibre install-path resolution.** [AlibreAddOn.vb:86-91](../AlibreAddOn.vb) derives the
  install root from the loaded `AlibreX.dll` location
  (`Assembly.GetAssembly(GetType(IADRoot)).Location.Replace(...)`) instead of hard-coding a path —
  a real improvement over the sibling add-on, which pinned `C:\Program Files\Alibre Design 28...`.
- **Defensive session lookup.** [AlibreAddOn.vb:48-67](../AlibreAddOn.vb) matches the session by
  identifier, falls back to the first session, and wraps everything in `Try/Catch`, surfacing
  errors via a single message box rather than crossing the COM boundary as an unhandled exception.
- **`SubMenuItems` returns a real array** (`New Integer() {CMD}`) for the known id, and the
  `SaveData`/`LoadData` overloads are safe no-ops (no `NotImplementedException` traps like the
  sibling repo had).
- **The section-property math is well structured.** `PolygonProperties` uses Green's-theorem
  shoelace integrals for area/centroid/second moments and correctly applies the parallel-axis
  shift to centroidal moments, then derives principal moments, radii of gyration, and section
  moduli. The closed-form `CircleProperties`/`AnnulusProperties` agree with standard formulae, and
  `Template.py` validates the computed area against `face.GetArea()`.
- **`alibre_setup.py` bootstrap** cleanly distinguishes part vs. assembly sessions and is injected
  before the main script — a sensible extension pattern.

---

## 7. Recommended fix order

1. **C-1** — make the `.iss` paths relative so a release can actually be built off a clean clone.
   (blocking)
2. **H-1 / H-4** — add (and copy) a real `logo.ico` or fix the manifest, and delete the phantom
   `AlibreScriptAddon.adc` / `icons\**` project items so the manifest and build are coherent.
3. **H-3** — fix or remove the misnamed `alibre-cross-section-tools-addon` → `AlibreScriptAddOn.dll`
   reference.
4. **H-2** — make `Template.py` use the injected `CurrentPart` so analysis runs against the invoked
   session.
5. **M-1** — correct the installer's `Alibre, Inc.` → `Alibre, LLC` registry check.
6. **M-2** — decide the fate of `adding-more-geometry-types.py` (wire it up + fix `CurrentPart()`,
   or remove it).
7. Sweep **M-3 / M-4 / L-*** (prints, menu labels, version alignment, unused imports, orphan PNGs)
   when touching the relevant files.
