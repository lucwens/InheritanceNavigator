# InheritanceNavigator — UI Design

## Main Tool Window

The InheritanceNavigator tool window is a vertical dockable panel similar to the Solution Explorer. It contains five sections stacked vertically, each with a collapsible header.

### Full Layout Prototype

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 920" width="320" height="920" font-family="Segoe UI, sans-serif" font-size="12">
  <!-- Window chrome -->
  <rect x="0" y="0" width="320" height="920" rx="4" fill="#1e1e1e" stroke="#3f3f46" stroke-width="1"/>
  <!-- Title bar -->
  <rect x="0" y="0" width="320" height="28" rx="4" fill="#2d2d30"/>
  <rect x="0" y="14" width="320" height="14" fill="#2d2d30"/>
  <text x="10" y="18" fill="#f1f1f1" font-size="12" font-weight="bold">Inheritance Navigator</text>
  <text x="290" y="18" fill="#999" font-size="14">×</text>
  <text x="272" y="18" fill="#999" font-size="10">▼</text>
  <text x="254" y="18" fill="#999" font-size="10">📌</text>

  <!-- ═══════════════════════════════════════════ -->
  <!-- SECTION 1: Source Folders                   -->
  <!-- ═══════════════════════════════════════════ -->
  <rect x="1" y="30" width="318" height="22" fill="#333337"/>
  <text x="18" y="45" fill="#f1f1f1" font-size="11" font-weight="bold">▾ Source Folders</text>
  <!-- Toolbar: cog, enable all, disable all -->
  <rect x="225" y="32" width="18" height="18" rx="2" fill="#3f3f46" stroke="#555" stroke-width="0.5"/>
  <text x="229" y="45" fill="#ccc" font-size="11">⚙</text>
  <rect x="247" y="32" width="34" height="18" rx="2" fill="#3f3f46" stroke="#555" stroke-width="0.5"/>
  <text x="251" y="45" fill="#ccc" font-size="9">All ✓</text>
  <rect x="285" y="32" width="30" height="18" rx="2" fill="#3f3f46" stroke="#555" stroke-width="0.5"/>
  <text x="289" y="45" fill="#ccc" font-size="9">None</text>

  <!-- Folder checkboxes -->
  <rect x="5" y="54" width="310" height="100" fill="#252526"/>
  <!-- Checkbox items -->
  <rect x="14" y="62" width="12" height="12" rx="2" fill="#3f3f46" stroke="#007acc" stroke-width="1.5"/>
  <text x="17" y="72" fill="#007acc" font-size="10" font-weight="bold">✓</text>
  <text x="32" y="72" fill="#dcdcdc" font-size="11">src/Core</text>

  <rect x="14" y="82" width="12" height="12" rx="2" fill="#3f3f46" stroke="#007acc" stroke-width="1.5"/>
  <text x="17" y="92" fill="#007acc" font-size="10" font-weight="bold">✓</text>
  <text x="32" y="92" fill="#dcdcdc" font-size="11">src/Rendering</text>

  <rect x="14" y="102" width="12" height="12" rx="2" fill="#3f3f46" stroke="#007acc" stroke-width="1.5"/>
  <text x="17" y="112" fill="#007acc" font-size="10" font-weight="bold">✓</text>
  <text x="32" y="112" fill="#dcdcdc" font-size="11">src/Physics</text>

  <rect x="14" y="122" width="12" height="12" rx="2" fill="#3f3f46" stroke="#555" stroke-width="1"/>
  <text x="32" y="132" fill="#888" font-size="11">vendor/ThirdParty</text>

  <rect x="14" y="142" width="12" height="12" rx="2" fill="#3f3f46" stroke="#555" stroke-width="1"/>
  <text x="32" y="152" fill="#888" font-size="11">vendor/External</text>

  <!-- ═══════════════════════════════════════════ -->
  <!-- SECTION 2: Class Selection                  -->
  <!-- ═══════════════════════════════════════════ -->
  <rect x="1" y="160" width="318" height="22" fill="#333337"/>
  <text x="18" y="175" fill="#f1f1f1" font-size="11" font-weight="bold">▾ Class</text>

  <!-- Search box -->
  <rect x="5" y="184" width="310" height="24" rx="3" fill="#3c3c3c" stroke="#007acc" stroke-width="1"/>
  <text x="10" y="200" fill="#007acc" font-size="11">🔍</text>
  <text x="28" y="200" fill="#cccccc" font-size="11">Render</text>
  <text x="64" y="200" fill="#555" font-size="11">|</text>

  <!-- Filtered class list -->
  <rect x="5" y="210" width="310" height="130" fill="#252526"/>
  <rect x="5" y="230" width="310" height="20" fill="#094771"/>
  <text x="14" y="225" fill="#dcdcdc" font-size="11">BaseRenderer</text>
  <text x="14" y="245" fill="#ffffff" font-size="11">MeshRenderer</text>
  <text x="14" y="265" fill="#dcdcdc" font-size="11">ParticleRenderer</text>
  <text x="14" y="285" fill="#dcdcdc" font-size="11">ShadowRenderer</text>
  <text x="14" y="305" fill="#dcdcdc" font-size="11">TextRenderer</text>
  <text x="14" y="325" fill="#dcdcdc" font-size="11">UIRenderer</text>

  <!-- ═══════════════════════════════════════════ -->
  <!-- SECTION 3: Virtual Functions                -->
  <!-- ═══════════════════════════════════════════ -->
  <rect x="1" y="345" width="318" height="22" fill="#333337"/>
  <text x="18" y="360" fill="#f1f1f1" font-size="11" font-weight="bold">▾ Virtual Functions</text>
  <text x="140" y="360" fill="#888" font-size="10">MeshRenderer</text>

  <!-- Search box -->
  <rect x="5" y="369" width="310" height="24" rx="3" fill="#3c3c3c" stroke="#555" stroke-width="1"/>
  <text x="10" y="385" fill="#888" font-size="11">🔍</text>
  <text x="28" y="385" fill="#555" font-size="11" font-style="italic">Type to filter functions...</text>

  <!-- Function list -->
  <rect x="5" y="395" width="310" height="100" fill="#252526"/>
  <rect x="5" y="415" width="310" height="20" fill="#094771"/>
  <text x="14" y="410" fill="#dcdcdc" font-size="11">virtual void Initialize()</text>
  <text x="14" y="430" fill="#ffffff" font-size="11">virtual void Render(const Scene&amp;)</text>
  <text x="14" y="450" fill="#dcdcdc" font-size="11">virtual void Shutdown()</text>
  <text x="14" y="470" fill="#dcdcdc" font-size="11">virtual void UpdateTransform()</text>
  <text x="14" y="490" fill="#dcdcdc" font-size="11">virtual bool IsVisible() const</text>

  <!-- ═══════════════════════════════════════════ -->
  <!-- SECTION 4: Inherited From                   -->
  <!-- ═══════════════════════════════════════════ -->
  <rect x="1" y="500" width="318" height="22" fill="#333337"/>
  <text x="18" y="515" fill="#f1f1f1" font-size="11" font-weight="bold">▾ Inherited From</text>
  <text x="120" y="515" fill="#888" font-size="10">Render(const Scene&amp;)</text>

  <!-- Linear ancestor list -->
  <rect x="5" y="524" width="310" height="80" fill="#252526"/>
  <text x="14" y="542" fill="#569cd6" font-size="11">↑</text>
  <text x="28" y="542" fill="#4ec9b0" font-size="11">BaseRenderer</text>
  <text x="120" y="542" fill="#666" font-size="10">BaseRenderer.cpp:142</text>
  <text x="14" y="562" fill="#569cd6" font-size="11">↑</text>
  <text x="28" y="562" fill="#4ec9b0" font-size="11">SceneObject</text>
  <text x="120" y="562" fill="#666" font-size="10">SceneObject.cpp:87</text>
  <text x="14" y="582" fill="#569cd6" font-size="11">↑</text>
  <text x="28" y="582" fill="#4ec9b0" font-size="11">IRenderable</text>
  <text x="120" y="582" fill="#666" font-size="10">(pure virtual)</text>

  <!-- Hint text -->
  <text x="14" y="600" fill="#555" font-size="9" font-style="italic">Double-click to navigate to implementation</text>

  <!-- ═══════════════════════════════════════════ -->
  <!-- SECTION 5: Derived Classes                  -->
  <!-- ═══════════════════════════════════════════ -->
  <rect x="1" y="610" width="318" height="22" fill="#333337"/>
  <text x="18" y="625" fill="#f1f1f1" font-size="11" font-weight="bold">▾ Derived Overrides</text>
  <text x="140" y="625" fill="#888" font-size="10">Render(const Scene&amp;)</text>

  <!-- Tree view of derived classes -->
  <rect x="5" y="634" width="310" height="280" fill="#252526"/>

  <!-- Tree structure with indentation -->
  <text x="14" y="652" fill="#dcdcaa" font-size="11">▾</text>
  <text x="28" y="652" fill="#4ec9b0" font-size="11">MeshRenderer</text>
  <text x="140" y="652" fill="#666" font-size="10">MeshRenderer.cpp:205</text>

  <text x="34" y="672" fill="#dcdcaa" font-size="11">▾</text>
  <text x="48" y="672" fill="#4ec9b0" font-size="11">SkinnedMeshRenderer</text>
  <text x="195" y="672" fill="#666" font-size="10">SkinnedMesh.cpp:89</text>

  <text x="54" y="692" fill="#dcdcaa" font-size="10">▸</text>
  <text x="68" y="692" fill="#4ec9b0" font-size="11">AnimatedMeshRenderer</text>
  <text x="215" y="692" fill="#666" font-size="10">AnimMesh.cpp:34</text>

  <text x="34" y="712" fill="#dcdcaa" font-size="10">▸</text>
  <text x="48" y="712" fill="#4ec9b0" font-size="11">LODMeshRenderer</text>
  <text x="175" y="712" fill="#666" font-size="10">LODMesh.cpp:56</text>

  <text x="14" y="737" fill="#dcdcaa" font-size="11">▾</text>
  <text x="28" y="737" fill="#4ec9b0" font-size="11">ParticleRenderer</text>
  <text x="155" y="737" fill="#666" font-size="10">ParticleRenderer.cpp:312</text>

  <text x="34" y="757" fill="#dcdcaa" font-size="10">▸</text>
  <text x="48" y="757" fill="#4ec9b0" font-size="11">GPUParticleRenderer</text>
  <text x="195" y="757" fill="#666" font-size="10">GPUParticle.cpp:78</text>

  <text x="14" y="782" fill="#dcdcaa" font-size="10">▸</text>
  <text x="28" y="782" fill="#4ec9b0" font-size="11">ShadowRenderer</text>
  <text x="140" y="782" fill="#666" font-size="10">ShadowRenderer.cpp:167</text>

  <text x="14" y="802" fill="#dcdcaa" font-size="10">▸</text>
  <text x="28" y="802" fill="#4ec9b0" font-size="11">TextRenderer</text>
  <text x="120" y="802" fill="#666" font-size="10">TextRenderer.cpp:93</text>

  <text x="14" y="822" fill="#dcdcaa" font-size="10">▸</text>
  <text x="28" y="822" fill="#4ec9b0" font-size="11">UIRenderer</text>
  <text x="110" y="822" fill="#666" font-size="10">UIRenderer.cpp:201</text>

  <!-- Hint text -->
  <text x="14" y="845" fill="#555" font-size="9" font-style="italic">Double-click to navigate to implementation</text>

  <!-- Status bar -->
  <rect x="0" y="900" width="320" height="20" fill="#007acc"/>
  <text x="10" y="914" fill="#ffffff" font-size="10">Ready — 847 classes indexed from 3 folders</text>
</svg>

---

## Section Details

### Section 1: Source Folders

The top section controls which source folders are included in the analysis. This is the primary mechanism for excluding external/third-party libraries.

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 180" width="400" height="180" font-family="Segoe UI, sans-serif" font-size="12">
  <rect x="0" y="0" width="400" height="180" fill="#1e1e1e"/>

  <!-- Header bar -->
  <rect x="0" y="0" width="400" height="26" fill="#333337"/>
  <text x="18" y="17" fill="#f1f1f1" font-size="12" font-weight="bold">▾ Source Folders</text>

  <!-- Toolbar buttons -->
  <rect x="270" y="3" width="24" height="20" rx="3" fill="#3f3f46" stroke="#555" stroke-width="0.5"/>
  <text x="276" y="17" fill="#ccc" font-size="13">⚙</text>
  <text x="267" y="38" fill="#666" font-size="8" text-anchor="middle">Settings</text>

  <rect x="300" y="3" width="44" height="20" rx="3" fill="#3f3f46" stroke="#555" stroke-width="0.5"/>
  <text x="306" y="17" fill="#ccc" font-size="10">All ✓</text>
  <text x="322" y="38" fill="#666" font-size="8" text-anchor="middle">Enable All</text>

  <rect x="350" y="3" width="44" height="20" rx="3" fill="#3f3f46" stroke="#555" stroke-width="0.5"/>
  <text x="358" y="17" fill="#ccc" font-size="10">None</text>
  <text x="372" y="38" fill="#666" font-size="8" text-anchor="middle">Disable All</text>

  <!-- Checkbox list -->
  <rect x="10" y="48" width="14" height="14" rx="2" fill="#3f3f46" stroke="#007acc" stroke-width="1.5"/>
  <text x="13" y="60" fill="#007acc" font-size="11" font-weight="bold">✓</text>
  <text x="30" y="60" fill="#dcdcdc" font-size="12">C:\Projects\MyApp\src\Core</text>
  <text x="325" y="60" fill="#888" font-size="10">312 classes</text>

  <rect x="10" y="70" width="14" height="14" rx="2" fill="#3f3f46" stroke="#007acc" stroke-width="1.5"/>
  <text x="13" y="82" fill="#007acc" font-size="11" font-weight="bold">✓</text>
  <text x="30" y="82" fill="#dcdcdc" font-size="12">C:\Projects\MyApp\src\Rendering</text>
  <text x="325" y="82" fill="#888" font-size="10">198 classes</text>

  <rect x="10" y="92" width="14" height="14" rx="2" fill="#3f3f46" stroke="#007acc" stroke-width="1.5"/>
  <text x="13" y="104" fill="#007acc" font-size="11" font-weight="bold">✓</text>
  <text x="30" y="104" fill="#dcdcdc" font-size="12">C:\Projects\MyApp\src\Physics</text>
  <text x="325" y="104" fill="#888" font-size="10">337 classes</text>

  <rect x="10" y="114" width="14" height="14" rx="2" fill="#3f3f46" stroke="#555" stroke-width="1"/>
  <text x="30" y="126" fill="#888" font-size="12">C:\Projects\MyApp\vendor\ThirdParty</text>

  <rect x="10" y="136" width="14" height="14" rx="2" fill="#3f3f46" stroke="#555" stroke-width="1"/>
  <text x="30" y="148" fill="#888" font-size="12">C:\Projects\MyApp\vendor\External</text>

  <!-- Divider -->
  <line x1="0" y1="165" x2="400" y2="165" stroke="#333" stroke-width="1"/>
</svg>

**Interactions:**
- **Cog button** opens a settings dialog to add/remove source folders
- **All/None buttons** toggle all checkboxes at once
- **Checkboxes** individually enable/disable folders; changing triggers re-filtering of the class list below
- Class count per folder shown on the right (when indexed)

---

### Section 2: Class Selection

A search field with text fragment matching and a filtered results list.

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 210" width="400" height="210" font-family="Segoe UI, sans-serif" font-size="12">
  <rect x="0" y="0" width="400" height="210" fill="#1e1e1e"/>

  <!-- Header -->
  <rect x="0" y="0" width="400" height="26" fill="#333337"/>
  <text x="18" y="17" fill="#f1f1f1" font-size="12" font-weight="bold">▾ Class</text>
  <text x="340" y="17" fill="#888" font-size="10">847 classes</text>

  <!-- Search box -->
  <rect x="8" y="32" width="384" height="26" rx="3" fill="#3c3c3c" stroke="#007acc" stroke-width="1.5"/>
  <text x="14" y="49" fill="#007acc" font-size="13">🔍</text>
  <text x="34" y="49" fill="#cccccc" font-size="12">Mesh</text>
  <rect x="60" y="38" width="1" height="14" fill="#007acc"/>

  <!-- Filtered results -->
  <rect x="8" y="62" width="384" height="26" fill="#094771"/>
  <text x="16" y="79" fill="#ffffff" font-size="12">MeshRenderer</text>
  <text x="296" y="79" fill="#aaa" font-size="10">Rendering</text>

  <rect x="8" y="88" width="384" height="26" fill="#252526"/>
  <text x="16" y="105" fill="#dcdcdc" font-size="12">MeshCollider</text>
  <text x="296" y="105" fill="#666" font-size="10">Physics</text>

  <rect x="8" y="114" width="384" height="26" fill="#252526"/>
  <text x="16" y="131" fill="#dcdcdc" font-size="12">MeshFilter</text>
  <text x="296" y="131" fill="#666" font-size="10">Core</text>

  <rect x="8" y="140" width="384" height="26" fill="#252526"/>
  <text x="16" y="157" fill="#dcdcdc" font-size="12">MeshBuilder</text>
  <text x="296" y="157" fill="#666" font-size="10">Core</text>

  <rect x="8" y="166" width="384" height="26" fill="#252526"/>
  <text x="16" y="183" fill="#dcdcdc" font-size="12">SkinnedMeshRenderer</text>
  <text x="296" y="183" fill="#666" font-size="10">Rendering</text>

  <line x1="0" y1="200" x2="400" y2="200" stroke="#333" stroke-width="1"/>
</svg>

**Interactions:**
- Typing in the search field filters the class list in real-time (debounced ~200ms)
- Text fragments match anywhere in the class name (substring match)
- Source folder name shown on the right for context
- Clicking a class selects it and populates the Virtual Functions section below
- Selected class highlighted in blue

---

### Section 3: Virtual Functions

Shows all virtual/overridable functions for the selected class, with the same search/filter pattern.

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 180" width="400" height="180" font-family="Segoe UI, sans-serif" font-size="12">
  <rect x="0" y="0" width="400" height="180" fill="#1e1e1e"/>

  <!-- Header -->
  <rect x="0" y="0" width="400" height="26" fill="#333337"/>
  <text x="18" y="17" fill="#f1f1f1" font-size="12" font-weight="bold">▾ Virtual Functions</text>
  <text x="155" y="17" fill="#4ec9b0" font-size="10">MeshRenderer</text>
  <text x="340" y="17" fill="#888" font-size="10">5 functions</text>

  <!-- Search box (empty/placeholder state) -->
  <rect x="8" y="32" width="384" height="26" rx="3" fill="#3c3c3c" stroke="#555" stroke-width="1"/>
  <text x="14" y="49" fill="#888" font-size="13">🔍</text>
  <text x="34" y="49" fill="#555" font-size="12" font-style="italic">Type to filter functions...</text>

  <!-- Function list -->
  <rect x="8" y="62" width="384" height="26" fill="#252526"/>
  <text x="16" y="79" fill="#dcdcaa" font-size="12">Initialize()</text>
  <text x="320" y="79" fill="#569cd6" font-size="10">virtual</text>

  <rect x="8" y="88" width="384" height="26" fill="#094771"/>
  <text x="16" y="105" fill="#ffffff" font-size="12">Render(const Scene&amp;)</text>
  <text x="312" y="105" fill="#569cd6" font-size="10">override</text>

  <rect x="8" y="114" width="384" height="26" fill="#252526"/>
  <text x="16" y="131" fill="#dcdcaa" font-size="12">Shutdown()</text>
  <text x="312" y="131" fill="#569cd6" font-size="10">override</text>

  <rect x="8" y="140" width="384" height="26" fill="#252526"/>
  <text x="16" y="157" fill="#dcdcaa" font-size="12">UpdateTransform()</text>
  <text x="320" y="157" fill="#569cd6" font-size="10">virtual</text>

  <line x1="0" y1="173" x2="400" y2="173" stroke="#333" stroke-width="1"/>
</svg>

**Interactions:**
- Same search/filter pattern as the class list
- Shows whether function is `virtual` (first declared here) or `override`
- Selecting a function populates both the Inherited From and Derived Overrides sections

---

### Section 4: Inherited From (Ancestor Chain)

A linear list showing the upward chain of classes that declare/implement this function.

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 130" width="400" height="130" font-family="Segoe UI, sans-serif" font-size="12">
  <rect x="0" y="0" width="400" height="130" fill="#1e1e1e"/>

  <!-- Header -->
  <rect x="0" y="0" width="400" height="26" fill="#333337"/>
  <text x="18" y="17" fill="#f1f1f1" font-size="12" font-weight="bold">▾ Inherited From</text>
  <text x="130" y="17" fill="#dcdcaa" font-size="10">Render(const Scene&amp;)</text>

  <!-- Ancestor chain (bottom-up: most direct base first) -->
  <rect x="8" y="30" width="384" height="26" fill="#252526"/>
  <text x="16" y="47" fill="#569cd6" font-size="14">↑</text>
  <text x="32" y="47" fill="#4ec9b0" font-size="12">BaseRenderer</text>
  <text x="240" y="47" fill="#666" font-size="10">BaseRenderer.cpp : 142</text>

  <rect x="8" y="56" width="384" height="26" fill="#252526"/>
  <text x="16" y="73" fill="#569cd6" font-size="14">↑</text>
  <text x="32" y="73" fill="#4ec9b0" font-size="12">SceneObject</text>
  <text x="240" y="73" fill="#666" font-size="10">SceneObject.cpp : 87</text>

  <rect x="8" y="82" width="384" height="26" fill="#252526"/>
  <text x="16" y="99" fill="#569cd6" font-size="14">↑</text>
  <text x="32" y="99" fill="#9b9b9b" font-size="12" font-style="italic">IRenderable</text>
  <text x="240" y="99" fill="#666" font-size="10">(pure virtual — no impl)</text>

  <!-- Hint -->
  <text x="8" y="122" fill="#555" font-size="9" font-style="italic">Double-click a row to open the source file at the function implementation</text>
</svg>

**Interactions:**
- Linear list, most direct base class at top, root of chain at bottom
- Each row shows: class name, source file, and line number
- Pure virtual functions are shown in italic with "(pure virtual)" note
- **Double-click** opens the source file and scrolls to the function implementation

---

### Section 5: Derived Overrides (Descendant Tree)

A hierarchical tree showing all classes that override this function, with depth indicating inheritance level.

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 280" width="400" height="280" font-family="Segoe UI, sans-serif" font-size="12">
  <rect x="0" y="0" width="400" height="280" fill="#1e1e1e"/>

  <!-- Header -->
  <rect x="0" y="0" width="400" height="26" fill="#333337"/>
  <text x="18" y="17" fill="#f1f1f1" font-size="12" font-weight="bold">▾ Derived Overrides</text>
  <text x="145" y="17" fill="#dcdcaa" font-size="10">Render(const Scene&amp;)</text>

  <!-- Tree view -->
  <!-- Level 0: MeshRenderer -->
  <rect x="8" y="30" width="384" height="24" fill="#252526"/>
  <text x="16" y="46" fill="#dcdcaa" font-size="12">▾</text>
  <text x="30" y="46" fill="#4ec9b0" font-size="12">MeshRenderer</text>
  <text x="260" y="46" fill="#666" font-size="10">MeshRenderer.cpp : 205</text>

  <!--   Level 1: SkinnedMeshRenderer -->
  <rect x="8" y="54" width="384" height="24" fill="#252526"/>
  <text x="36" y="70" fill="#dcdcaa" font-size="12">▾</text>
  <text x="50" y="70" fill="#4ec9b0" font-size="12">SkinnedMeshRenderer</text>
  <text x="260" y="70" fill="#666" font-size="10">SkinnedMesh.cpp : 89</text>

  <!--     Level 2: AnimatedMeshRenderer -->
  <rect x="8" y="78" width="384" height="24" fill="#252526"/>
  <text x="56" y="94" fill="#dcdcaa" font-size="11">▸</text>
  <text x="70" y="94" fill="#4ec9b0" font-size="12">AnimatedMeshRenderer</text>
  <text x="260" y="94" fill="#666" font-size="10">AnimMesh.cpp : 34</text>

  <!--   Level 1: LODMeshRenderer -->
  <rect x="8" y="102" width="384" height="24" fill="#252526"/>
  <text x="36" y="118" fill="#dcdcaa" font-size="11">▸</text>
  <text x="50" y="118" fill="#4ec9b0" font-size="12">LODMeshRenderer</text>
  <text x="260" y="118" fill="#666" font-size="10">LODMesh.cpp : 56</text>

  <!-- Level 0: ParticleRenderer -->
  <rect x="8" y="130" width="384" height="24" fill="#252526"/>
  <text x="16" y="146" fill="#dcdcaa" font-size="12">▾</text>
  <text x="30" y="146" fill="#4ec9b0" font-size="12">ParticleRenderer</text>
  <text x="260" y="146" fill="#666" font-size="10">ParticleRenderer.cpp : 312</text>

  <!--   Level 1: GPUParticleRenderer -->
  <rect x="8" y="154" width="384" height="24" fill="#252526"/>
  <text x="36" y="170" fill="#dcdcaa" font-size="11">▸</text>
  <text x="50" y="170" fill="#4ec9b0" font-size="12">GPUParticleRenderer</text>
  <text x="260" y="170" fill="#666" font-size="10">GPUParticle.cpp : 78</text>

  <!-- Level 0: ShadowRenderer (leaf) -->
  <rect x="8" y="182" width="384" height="24" fill="#252526"/>
  <text x="16" y="198" fill="#dcdcaa" font-size="11">▸</text>
  <text x="30" y="198" fill="#4ec9b0" font-size="12">ShadowRenderer</text>
  <text x="260" y="198" fill="#666" font-size="10">ShadowRenderer.cpp : 167</text>

  <!-- Level 0: TextRenderer (leaf) -->
  <rect x="8" y="206" width="384" height="24" fill="#252526"/>
  <text x="16" y="222" fill="#dcdcaa" font-size="11">▸</text>
  <text x="30" y="222" fill="#4ec9b0" font-size="12">TextRenderer</text>
  <text x="260" y="222" fill="#666" font-size="10">TextRenderer.cpp : 93</text>

  <!-- Level 0: UIRenderer (leaf) -->
  <rect x="8" y="230" width="384" height="24" fill="#252526"/>
  <text x="16" y="246" fill="#dcdcaa" font-size="11">▸</text>
  <text x="30" y="246" fill="#4ec9b0" font-size="12">UIRenderer</text>
  <text x="260" y="246" fill="#666" font-size="10">UIRenderer.cpp : 201</text>

  <!-- Hint -->
  <text x="8" y="270" fill="#555" font-size="9" font-style="italic">Double-click a row to open the source file at the function implementation. ▾/▸ expand/collapse subtrees.</text>
</svg>

**Interactions:**
- Hierarchical tree with expand/collapse (▾/▸)
- Indentation indicates depth in the inheritance chain
- Each node shows: class name, source file, and line number of the override implementation
- Only classes that actually override the function appear (classes that inherit without overriding are omitted)
- **Double-click** opens the source file and scrolls to the function implementation

---

## Settings Dialog (Cog Button)

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 450 280" width="450" height="280" font-family="Segoe UI, sans-serif" font-size="12">
  <rect x="0" y="0" width="450" height="280" rx="4" fill="#2d2d30" stroke="#3f3f46" stroke-width="1"/>

  <!-- Title bar -->
  <rect x="0" y="0" width="450" height="30" rx="4" fill="#3f3f46"/>
  <rect x="0" y="15" width="450" height="15" fill="#3f3f46"/>
  <text x="14" y="20" fill="#f1f1f1" font-size="12" font-weight="bold">Inheritance Navigator — Source Folder Settings</text>
  <text x="430" y="20" fill="#999" font-size="14">×</text>

  <!-- Folder list -->
  <rect x="14" y="40" width="356" height="180" rx="2" fill="#1e1e1e" stroke="#3f3f46" stroke-width="1"/>

  <rect x="16" y="42" width="352" height="22" fill="#252526"/>
  <text x="22" y="57" fill="#dcdcdc" font-size="11">C:\Projects\MyApp\src\Core</text>

  <rect x="16" y="64" width="352" height="22" fill="#094771"/>
  <text x="22" y="79" fill="#ffffff" font-size="11">C:\Projects\MyApp\src\Rendering</text>

  <rect x="16" y="86" width="352" height="22" fill="#252526"/>
  <text x="22" y="101" fill="#dcdcdc" font-size="11">C:\Projects\MyApp\src\Physics</text>

  <rect x="16" y="108" width="352" height="22" fill="#252526"/>
  <text x="22" y="123" fill="#dcdcdc" font-size="11">C:\Projects\MyApp\vendor\ThirdParty</text>

  <rect x="16" y="130" width="352" height="22" fill="#252526"/>
  <text x="22" y="145" fill="#dcdcdc" font-size="11">C:\Projects\MyApp\vendor\External</text>

  <!-- Action buttons on the right -->
  <rect x="380" y="42" width="56" height="24" rx="3" fill="#0e639c" stroke="#007acc" stroke-width="0.5"/>
  <text x="394" y="58" fill="#fff" font-size="10">Add...</text>

  <rect x="380" y="72" width="56" height="24" rx="3" fill="#3f3f46" stroke="#555" stroke-width="0.5"/>
  <text x="390" y="88" fill="#ccc" font-size="10">Remove</text>

  <rect x="380" y="102" width="56" height="24" rx="3" fill="#3f3f46" stroke="#555" stroke-width="0.5"/>
  <text x="393" y="118" fill="#ccc" font-size="10">Move ↑</text>

  <rect x="380" y="132" width="56" height="24" rx="3" fill="#3f3f46" stroke="#555" stroke-width="0.5"/>
  <text x="393" y="148" fill="#ccc" font-size="10">Move ↓</text>

  <!-- OK / Cancel -->
  <rect x="280" y="236" width="72" height="28" rx="3" fill="#0e639c" stroke="#007acc" stroke-width="0.5"/>
  <text x="305" y="254" fill="#fff" font-size="11" text-anchor="middle">OK</text>

  <rect x="362" y="236" width="72" height="28" rx="3" fill="#3f3f46" stroke="#555" stroke-width="0.5"/>
  <text x="390" y="254" fill="#ccc" font-size="11" text-anchor="middle">Cancel</text>
</svg>

**Interactions:**
- **Add...** opens a folder browser dialog
- **Remove** deletes the selected folder from the list
- **Move Up/Down** reorders folders
- Settings are persisted per-solution in a `.inheritancenav.json` file or via VS settings

---

## Color Scheme Notes

The prototypes above use the **Visual Studio Dark Theme** color palette:
- Background: `#1e1e1e` (editor), `#252526` (panels), `#333337` (headers)
- Text: `#dcdcdc` (normal), `#f1f1f1` (bright), `#888` (dimmed)
- Accent: `#007acc` (selection, focus), `#094771` (selected row)
- Types: `#4ec9b0` (class names — VS teal), `#dcdcaa` (function names — VS yellow)
- Keywords: `#569cd6` (blue for virtual/override markers)

The extension should respect the user's active VS theme (Dark, Light, Blue) by using VS theme resources (`EnvironmentColors`) rather than hardcoded colors.
