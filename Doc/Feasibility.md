# InheritanceNavigator — Feasibility Analysis

**Date:** 2026-04-02  
**Status:** Pre-development / Planning phase

---

## 1. Project Overview

InheritanceNavigator is a proposed Visual Studio extension that provides a dockable tool window for navigating C++ class inheritance hierarchies. Its core value proposition is filtering out noise from external libraries and giving developers a focused, searchable view of virtual function overrides across their own codebase.

**Key features:**
- Source folder filtering to exclude external libraries
- Searchable class list with text fragment matching
- Searchable virtual function list for a selected class
- "Inherited From" view — linear list of base classes implementing a function
- "Derived From" view — tree of derived classes overriding a function
- Double-click navigation to function implementations (not declarations)

**Target platforms:** Visual Studio 2026 (required), Visual Studio 2022 (nice to have)

---

## 2. Executive Summary

InheritanceNavigator is **technically feasible**. The core challenge — reliably parsing C++ inheritance hierarchies and virtual function override chains — can be solved through multiple approaches, each with distinct trade-offs. Visual Studio's extensibility model for tool windows and file navigation is mature and well-documented. The VS 2022 to VS 2026 compatibility story is favorable, with Microsoft's API-version-based model meaning a single extension binary can target both versions. The project carries **moderate technical risk**, concentrated almost entirely in the C++ parsing layer.

---

## 3. Technical Feasibility

### 3.1 C++ Code Analysis — The Central Challenge

The extension needs to extract four pieces of information from a C++ codebase:
1. Class declarations and their names
2. Inheritance relationships (which class derives from which)
3. Virtual function declarations per class
4. Override relationships (which derived classes override which virtual functions) and the source locations of those **implementations** (not declarations)

C++ is notoriously difficult to parse. Unlike C# (where Roslyn provides a complete semantic model), there is no single, universally reliable, easy-to-integrate C++ parser for the .NET ecosystem. Five approaches were evaluated:

### 3.2 Approach Comparison

| Approach | Accuracy | Integration | Maintenance | Complexity | Verdict |
|----------|----------|-------------|-------------|------------|---------|
| ClangSharp / libclang | High | Medium | Medium | High | **Recommended** |
| VCCodeModel (DTE) | Medium | Excellent | Low | Low | Fallback |
| VS IntelliSense DB | High | Good | High | Medium | Too fragile |
| ctags / Universal Ctags | Low | Poor | Low | Low | Insufficient |
| Tree-sitter | Low | Poor | Medium | Medium | Insufficient |

#### Approach A: ClangSharp / libclang (Recommended)

[ClangSharp](https://github.com/dotnet/ClangSharp) provides .NET bindings to libclang, the stable C interface to Clang's AST. The extension would parse each translation unit, walk the AST to find class declarations, base specifiers, and method cursors, and use `clang_getOverriddenCursors()` to build override chains. ClangSharp.Interop (v21.x, January 2026) tracks LLVM 21 and is actively maintained under the `dotnet` GitHub organization.

- *Pros:*
  - Full semantic understanding of C++ (templates, multiple inheritance, virtual inheritance, SFINAE, macros)
  - Dedicated `clang_getOverriddenCursors()` API designed exactly for this use case
  - Provides precise source locations for both declarations and definitions via `clang_getCursorDefinition()`
  - Actively maintained, NuGet-distributable, works from C#
  - Independent of Visual Studio's internal C++ engine — works even if VS IntelliSense is broken or still loading
- *Cons:*
  - Requires compilation flags (include paths, defines, language standard) for each translation unit to parse correctly
  - Distributing libclang native binaries adds ~30-50 MB to the VSIX package
  - Parsing an entire large codebase from scratch can be slow (minutes for 100k+ LOC projects)
  - May disagree with MSVC on edge cases (MSVC extensions, non-standard code)
- *Viability:* **HIGH.** This is the most technically sound approach. The main integration challenge is obtaining compilation flags from the VS project system.

#### Approach B: VCCodeModel (Visual Studio's Built-in C++ Code Model)

Visual Studio exposes a `VCCodeModel` interface that provides access to C++ code elements parsed by VS's own IntelliSense engine.

- *Pros:* Zero additional parsing infrastructure, no native binaries to distribute, automatically has the correct compilation context
- *Cons:* VCCodeModel is a legacy, heuristic-based API. Microsoft has stated that type strings "are coming directly from source code" and "are no longer resolved by the compiler." It may not correctly resolve inheritance through typedefs, templates, or macros. It does not reliably distinguish between declarations and definitions. Limited documentation; the most detailed blog post is from 2010.
- *Viability:* **MEDIUM.** Works for simple hierarchies but may produce incorrect results for complex C++ code.

#### Approach C: VS IntelliSense Browse Database

Query the `.vs/` SQLite database containing parsed symbol information.

- *Pros:* Data already computed by VS. No redundant parsing needed.
- *Cons:* Schema is undocumented, changes between VS versions, concurrent access issues while VS is running.
- *Viability:* **LOW.** Too fragile for a production extension that must work across VS versions.

#### Approach D: Universal Ctags

Run ctags externally to generate a tags database, parse for class and function information.

- *Pros:* Very fast, simple to integrate.
- *Cons:* Purely syntactic — cannot resolve templates, macros, conditional compilation, or override relationships. Cannot locate implementations separately from declarations.
- *Viability:* **LOW.** Insufficient semantic accuracy for the stated requirements.

#### Approach E: Tree-sitter

Use a Tree-sitter C++ grammar to parse source files into concrete syntax trees.

- *Pros:* Fast incremental parsing, good error recovery.
- *Cons:* Syntactic only — no semantic analysis. Cannot resolve typedefs, templates, or namespaces. No .NET bindings of production quality.
- *Viability:* **LOW.** Same fundamental limitation as ctags.

### 3.3 Visual Studio Extension Framework — Low Risk

Creating a dockable tool window in Visual Studio is a well-established pattern. The VS SDK (VSSDK) provides:

- **Tool Window infrastructure** (`ToolWindowPane`) — dockable, floatable, pinnable windows identical to Solution Explorer
- **WPF-based UI** — full access to WPF for building the filtering/search interface with `TreeView`, `ListView`, `TextBox` controls
- **Command infrastructure** — toolbar buttons, context menus, keyboard shortcuts
- **Settings/options pages** — for persisting source folder configuration

The [Community.VisualStudio.Toolkit](https://github.com/VsixCommunity/Community.VisualStudio.Toolkit) NuGet package simplifies many VSSDK patterns and is recommended.

### 3.4 Extension Model Choice

| Aspect | VSSDK (Classic, In-Process) | VisualStudio.Extensibility (New, Out-of-Process) |
|--------|----------------------------|--------------------------------------------------|
| Tool Windows | Full WPF support | Remote UI (data binding only, no code-behind) |
| File Navigation | `IVsTextManager.NavigateToLineAndColumn` | Limited, still evolving |
| C++ Code Model Access | `VCCodeModel` via COM | Not available |
| Project System Access | Full DTE/IVsHierarchy | Project Query API (limited) |
| VS 2022 + VS 2026 | Yes (single binary) | VS 2022 17.9+ and VS 2026 |

**Recommendation:** Use **VSSDK (classic in-process)** for this extension. The requirement to access the C++ project system for compilation flags, create a rich interactive tool window, and navigate to specific source locations all favor the mature VSSDK model.

### 3.5 VS 2022 / VS 2026 Compatibility — Low Risk

Microsoft's API-version-based compatibility model means a VSIX targeting `[17.0,)` will load in both VS 2022 and VS 2026 without modification. Both versions are 64-bit and share the same SDK surface.

### 3.6 Source File Navigation — Low Risk

When using ClangSharp, both declaration and definition locations are available from the AST via `clang_getCursorDefinition()`. The extension stores the file path, line, and column of each function definition, then uses `IVsTextManager.NavigateToLineAndColumn()` to open and scroll to the exact location.

---

## 4. Recommended Architecture

### Primary: ClangSharp / libclang

ClangSharp is the only approach that provides the semantic accuracy required by the specification — particularly for the requirement to navigate to function **implementations** (not declarations), and for accurately resolving override chains through templates and complex inheritance.

### Compilation flag acquisition

The key integration challenge is obtaining compilation flags for libclang. This can be solved by:
1. Extracting compiler flags from the VS project system via `VCProject` / `VCConfiguration` / `VCCLCompilerTool` interfaces
2. Reading `compile_commands.json` if present (common in CMake projects)
3. Allowing manual configuration of include paths and defines in the extension's settings

### Architecture

Design the code analysis layer behind an interface so the parsing backend can be swapped or augmented without changing the UI layer:

```
UI Layer (WPF Tool Window)
    │
    ▼
IInheritanceAnalyzer (interface)
    │
    ├── ClangInheritanceAnalyzer (primary)
    └── DteInheritanceAnalyzer (lightweight fallback, if needed)
```

---

## 5. Key Risks and Mitigations

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| **Compilation flag acquisition** — ClangSharp requires accurate flags to parse correctly | High | Medium | Extract from VS project properties (`VCCLCompilerTool`). Support `compile_commands.json`. Allow manual override. Degrade gracefully with warnings. |
| **Performance on large codebases** — full libclang parsing can take minutes | High | Medium | Background threading. Cache index to disk. Re-parse only changed files. Use `CXTranslationUnit_SkipFunctionBodies` flag. Scope reduction via folder filtering. Progress indicator. |
| **VSIX package size** — libclang adds 30-50 MB | Medium | High | Use platform-specific NuGet runtime packages. Acceptable size for a developer tool. |
| **Complex C++ constructs** — templates, CRTP, virtual inheritance | Medium | Medium | libclang handles these correctly (it is a real compiler frontend). UI must handle multiple inheritance paths and diamond inheritance. |
| **VS 2022 vs 2026 API differences** | Medium | Low | Target `[17.0,)` for single binary. Test on both versions early. |
| **Stale index data** as code is edited | Medium | Medium | Listen to `IVsRunningDocTableEvents` for file saves. Provide manual Refresh button. Background re-indexing with debouncing. |
| **MSVC vs Clang disagreements** on non-standard code | Low | Low | Document known limitations. Most production C++ code compiles on both. |

---

## 6. Effort Estimation

| Component | Size | Estimated Effort | Notes |
|-----------|------|------------------|-------|
| Project scaffolding (VSIX, package, tool window) | S | 1-2 days | Use Community.VisualStudio.Toolkit |
| Tool window UI (WPF panels, search, tree views) | M | 3-5 days | Standard WPF + MVVM |
| Source folder configuration (settings, persistence) | S | 1-2 days | VS settings API or custom JSON config |
| ClangSharp integration (parsing pipeline, AST walking) | L | 5-8 days | Core complexity: classes, bases, virtuals, overrides |
| Compilation flag extraction (VS project system, JSON) | M | 3-5 days | COM interop with VCProject |
| Index/cache layer (in-memory model, disk, incremental) | M-L | 4-6 days | Performance-critical; file change detection |
| Search/filter logic (text fragment matching) | S | 1-2 days | Simple substring matching |
| "Inherited From" view (ancestor chain) | S | 1-2 days | Walk base class chain upward |
| "Derived From" tree view (overriding classes) | M | 2-3 days | Recursive tree construction |
| Double-click navigation | S | 1 day | `IVsTextManager.NavigateToLineAndColumn` |
| Testing and debugging | L | 5-8 days | Real C++ projects, edge cases |
| Polish and packaging (icons, marketplace) | S-M | 2-3 days | |

### Total Estimate

| Scenario | Duration |
|----------|----------|
| **Optimistic** (experienced VS extension developer) | 4-6 weeks |
| **Realistic** (competent C# developer, learning VS extensibility) | 8-12 weeks |
| **Pessimistic** (significant learning curve on both libclang and VSSDK) | 14-18 weeks |

The ClangSharp integration combined with compilation flag extraction and index caching represents roughly 40-50% of the total effort.

---

## 7. Dependencies and Prerequisites

### Required
- **Visual Studio 2026** with the "Visual Studio extension development" workload
- **.NET Framework 4.7.2+** (for VSSDK in-process extensions)
- **Microsoft.VisualStudio.SDK** NuGet package (17.x) — core VSSDK
- **Community.VisualStudio.Toolkit.17** NuGet package — simplified VSSDK wrapper
- **ClangSharp.Interop** NuGet package (21.x) — libclang .NET bindings
- **libclang** NuGet runtime package — native libclang binaries
- **A representative C++ codebase** — for testing and validating analysis accuracy

### Optional
- **CppAst.NET** — higher-level wrapper over ClangSharp if the raw API is too verbose

### Knowledge Requirements
- C# / WPF / MVVM
- Visual Studio VSSDK extensibility patterns (packages, tool windows, services)
- libclang API concepts (cursors, translation units, AST traversal)
- C++ language semantics (inheritance, virtual dispatch, override specifier)

---

## 8. Recommended Development Phases

### Phase 1 — Proof of Concept (2-3 weeks)
Build a minimal VSIX with a tool window that uses ClangSharp to parse a hardcoded folder, displays a class list, and shows base/derived classes for a selected class. **This validates the core technical risk** (ClangSharp integration within a VS extension).

### Phase 2 — Core Features (4-6 weeks)
Add virtual function enumeration, override chain resolution, source folder filtering, text search, and double-click navigation. Integrate compilation flag extraction from the VS project system.

### Phase 3 — Robustness (2-4 weeks)
Add background parsing, disk caching, incremental re-indexing on file changes, progress indicators, error handling for unparseable files, and testing against real-world C++ projects.

### Phase 4 — Polish (1-2 weeks)
Settings UI, icons, marketplace packaging, documentation, known-limitations list.

---

## 9. Existing Work and References

- [ClangSharp](https://github.com/dotnet/ClangSharp) — the recommended C++ parsing library; maintained under the dotnet GitHub organization
- [Community.VisualStudio.Toolkit](https://github.com/VsixCommunity/Community.VisualStudio.Toolkit) — recommended VSSDK wrapper with tool window and navigation samples
- [ClassHierarchyNavigator](https://github.com/csabeszko/ClassHierarchyNavigator) — VS 2022 type hierarchy extension (targets .NET/Roslyn, not C++, but useful architectural reference)
- [VCCodeModel Interface (Microsoft Learn)](https://learn.microsoft.com/en-us/dotnet/api/microsoft.visualstudio.vccodemodel.vccodemodel?view=visualstudiosdk-2022) — VS built-in C++ code model documentation
- [VS Extension Compatibility Model](https://devblogs.microsoft.com/visualstudio/modernizing-visual-studio-extension-compatibility-effortless-migration-for-extension-developers-and-users/) — API-version-based compatibility for VS 2022/2026
- [libclang documentation](https://clang.llvm.org/docs/LibClang.html) — Clang stable C API reference
- [clang_getOverriddenCursors](https://clang.llvm.org/doxygen/group__CINDEX__CURSOR__MANIP.html) — the key API for resolving override chains

---

## 10. Conclusion

### Verdict: PROCEED — the project is feasible

InheritanceNavigator fills a genuine gap in the C++ developer experience within Visual Studio. While VS provides "Go to Definition" and "Find All References," it lacks a dedicated, filtered view of inheritance hierarchies — exactly what this tool provides.

**Key recommendations:**

1. **Use ClangSharp as the primary analysis engine** — it is the only approach with sufficient semantic accuracy for C++ virtual function analysis, particularly for navigating to implementations
2. **Execute Phase 1 first as a time-boxed spike** — if the ClangSharp integration within a VSIX proves unworkable (native binary loading issues, parsing accuracy problems, or unacceptable performance), the project should be re-evaluated before proceeding
3. **Design for swappable backends** — abstract the code analysis behind an interface so the parsing strategy can evolve without rewriting the UI
4. **Target VS 2026 first** — get it working on the required platform before investing in VS 2022 back-compatibility
5. **Test with real-world C++ code early and often** — validate against the actual target codebase during Phase 1

The main risk is concentrated in the ClangSharp integration layer (compilation flag acquisition and performance on large codebases). All other components (UI, navigation, filtering) are standard VS extension patterns with low technical risk. With the phased approach, the critical risks are validated early, keeping overall project risk manageable.
