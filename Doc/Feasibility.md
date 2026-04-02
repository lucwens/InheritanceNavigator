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

## 2. Technical Feasibility

### 2.1 Overall Assessment: FEASIBLE

The project is technically feasible. All required capabilities have precedents in existing Visual Studio extensions. However, the **C++ code analysis component** is the most challenging aspect and will require careful technology selection.

### 2.2 Component Analysis

#### A. Visual Studio Extension Framework — Low Risk

Creating a dockable tool window in Visual Studio is a well-established pattern. The VS SDK (VSSDK) provides:

- **Tool Window infrastructure** (`ToolWindowPane`) — dockable, floatable, pinnable windows identical to Solution Explorer
- **WPF-based UI** — full access to WPF for building the filtering/search interface
- **Command infrastructure** — toolbar buttons, context menus, keyboard shortcuts
- **Settings/options pages** — for persisting source folder configuration

**Assessment:** Straightforward. Extensive documentation, templates, and samples exist. The `Microsoft.VisualStudio.SDK` NuGet package provides all necessary APIs.

#### B. C++ Code Analysis — High Risk (Core Challenge)

This is the central technical challenge. The extension needs to:
1. Enumerate all C++ classes within configured source folders
2. Identify virtual functions for each class
3. Resolve the full inheritance chain (both up and down) for each virtual function
4. Map each override to its source file and implementation location

**Five approaches were evaluated:**

| Approach | Accuracy | Integration | Maintenance | Complexity |
|----------|----------|-------------|-------------|------------|
| VS Code Model (DTE) | Medium | Excellent | Low | Low |
| libclang / ClangSharp | High | Poor | Medium | High |
| VS IntelliSense DB | High | Good | High | Medium |
| IVsLanguageService | Medium-High | Good | Medium | Medium |
| ctags | Low | Poor | Low | Low |

**Approach 1: Visual Studio Code Model (EnvDTE)**

The `EnvDTE.CodeModel` and `EnvDTE80.CodeModel2` APIs provide access to the code structure of a project as Visual Studio understands it.

- *Pros:* Fully integrated, no external dependencies, works with whatever parser VS uses internally, respects project configuration (include paths, defines)
- *Cons:* The C++ code model has historically been less complete than the C# one. `CodeClass.Bases` and `CodeClass.DerivedTypes` properties may not fully resolve complex template hierarchies. The `virtual` and `override` qualifiers may require inspecting `CodeFunction.FunctionKind` or parsing attributes manually
- *Viability:* Good starting point. Sufficient for most real-world C++ codebases that use straightforward inheritance

**Approach 2: libclang / ClangSharp**

Use LLVM's libclang through the ClangSharp C# bindings to parse C++ translation units into a full AST.

- *Pros:* Full, accurate C++ parsing including templates, multiple inheritance, virtual specifiers, override attributes. Industry-standard C++ parser
- *Cons:* Requires a compilation database (`compile_commands.json`) or manual configuration of include paths and defines. Adds a significant external dependency (~50MB+). Parsing large codebases can be slow. May disagree with MSVC on edge cases (MSVC extensions, non-standard code)
- *Viability:* Most accurate option, but heaviest integration burden

**Approach 3: VS IntelliSense Browse Database**

Visual Studio maintains a SQLite database (in the `.vs/` folder) containing parsed symbol information used by IntelliSense, Go to Definition, and Find All References.

- *Pros:* Data is already computed by VS during normal operation. Contains class hierarchies, function signatures, and source locations. No redundant parsing needed
- *Cons:* The database schema is undocumented and internal to VS. It changes between VS versions (a concern for VS 2022 + 2026 support). Accessing it requires reverse-engineering or using undocumented APIs. Concurrent access while VS is running may cause locking issues
- *Viability:* Potentially very efficient, but fragile and risky due to undocumented internals

**Approach 4: IVsLanguageService / Language Server Protocol**

Use Visual Studio's language service interfaces to query semantic information about C++ code.

- *Pros:* Official VS API surface, better maintained than raw DTE CodeModel. Can leverage whatever parsing engine VS uses (EDG-based for MSVC). Supports Find All References and Go to Definition semantics
- *Cons:* The C++ language service APIs are less documented than C#/VB equivalents. May require experimentation to find the right interfaces. API surface may change between VS versions
- *Viability:* Good middle ground between DTE simplicity and libclang accuracy

**Approach 5: Universal Ctags**

Run ctags externally to generate a tags file, then parse it for class and function information.

- *Pros:* Simple, fast, language-agnostic, no VS API dependency for parsing
- *Cons:* Poor accuracy for C++ — does not reliably resolve templates, namespaces, multiple inheritance, or virtual/override semantics. Would miss many real-world patterns
- *Viability:* Not recommended as primary approach. Accuracy is insufficient for the stated requirements

#### C. Source Folder Filtering — Low Risk

Filtering classes by source folder is straightforward regardless of the code analysis approach chosen. All approaches provide source file location information, which can be matched against configured folder paths.

#### D. Search/Filter UI — Low Risk

Text fragment matching on class names and function names is a standard UI pattern. WPF provides `CollectionViewSource` with filtering, or a simple LINQ-based filter on the backing data. Debounced text input with filtered list display is well-established.

#### E. Source File Navigation — Low Risk

Visual Studio provides multiple APIs for navigating to code locations:
- `DTE.ItemOperations.OpenFile()` + `TextSelection.GotoLine()`
- `IVsTextManager.NavigateToLineAndColumn()`
- `IVsCodeWindow` interfaces

Navigating to implementations (not declarations) is slightly more complex — it requires resolving which file contains the function body, not just the declaration. The code analysis approach chosen will determine how this information is obtained.

---

## 3. Recommended Approach

### Primary: Visual Studio Code Model (DTE) + IVsLanguageService

Start with the DTE Code Model as the foundation. It provides the simplest integration path and handles the majority of C++ inheritance patterns correctly. Supplement with `IVsLanguageService` APIs where the Code Model falls short (e.g., distinguishing virtual vs. override, resolving implementation locations).

### Fallback consideration: libclang

If the DTE Code Model proves insufficient for the target codebases (e.g., heavy template metaprogramming, complex multiple inheritance), libclang via ClangSharp can be introduced as an alternative analysis backend. This should be treated as a Phase 2 enhancement, not part of the initial implementation.

### Architecture recommendation

Design the code analysis layer behind an interface (`IInheritanceAnalyzer`) so the parsing backend can be swapped or augmented without changing the UI layer:

```
UI Layer (WPF Tool Window)
    │
    ▼
IInheritanceAnalyzer (interface)
    │
    ├── DteInheritanceAnalyzer (Phase 1)
    └── ClangInheritanceAnalyzer (Phase 2, if needed)
```

---

## 4. Key Risks and Mitigations

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| DTE Code Model insufficient for C++ virtual/override detection | High | Medium | Prototype early with real target codebase. Have libclang as fallback plan |
| VS 2022 vs 2026 API incompatibilities | Medium | Medium | Use the lowest common API surface. Test on both versions early. Consider separate VSIX targets if needed |
| Performance with large codebases (10K+ classes) | Medium | Medium | Cache analysis results. Use background threading. Only re-analyze changed files. Limit scope via folder filtering |
| Finding function implementations (not declarations) | Medium | Low | DTE provides `CodeFunction.StartPoint` which points to the definition. For header-only code, declaration = implementation |
| Extension marketplace / deployment complexity | Low | Low | Standard VSIX packaging. Well-documented process |
| Concurrent access to VS internals from extension | Medium | Low | Use VS threading model (`JoinableTaskFactory`). All VS API calls on the UI thread or via proper async patterns |

---

## 5. Effort Estimation

| Component | T-shirt Size | Estimated Effort | Notes |
|-----------|-------------|------------------|-------|
| VS Extension scaffold + tool window | S | 1-2 days | Project setup, VSIX manifest, empty tool window |
| Source folder settings UI | S | 1-2 days | Options page, settings persistence, folder picker |
| Source folder filter checkboxes | S | 1 day | Top-level UI component with enable/disable all |
| Class enumeration + search | M | 3-5 days | DTE Code Model integration, text fragment filtering |
| Virtual function enumeration + search | M | 3-5 days | Function listing, virtual/override detection |
| "Inherited From" view | M | 3-5 days | Walk base class chain, display list, navigation |
| "Derived From" tree view | L | 5-8 days | Recursive derived class resolution, tree rendering |
| Navigation to implementations | M | 2-3 days | Open file, scroll to function body |
| Caching and performance | M | 3-5 days | Background analysis, incremental updates |
| Testing and polish | M | 3-5 days | Manual testing on real codebases, edge cases |
| VS 2022 compatibility | S-M | 2-3 days | Conditional compilation or separate targets |

**Total estimated effort: 6-10 weeks** for a single developer, assuming familiarity with VS extensibility. Add 2-4 weeks if this is a first VS extension project (learning curve).

---

## 6. Dependencies and Prerequisites

### Required
- **Visual Studio 2026 SDK** — for extension development and testing
- **.NET / C#** — VS extensions are written in C#
- **Microsoft.VisualStudio.SDK** NuGet package — core VS extensibility APIs
- **A representative C++ codebase** — for testing and validating the analysis accuracy

### Optional (Phase 2)
- **ClangSharp** NuGet package — if libclang-based analysis is needed
- **LLVM/Clang runtime** — required by ClangSharp

### Development Environment
- Visual Studio 2026 with the "Visual Studio extension development" workload installed
- A test C++ solution with known inheritance hierarchies for validation

---

## 7. Conclusion and Recommendation

### Verdict: PROCEED — the project is feasible

The InheritanceNavigator fills a genuine gap in the C++ developer experience within Visual Studio. While VS provides "Go to Definition" and "Find All References," it lacks a dedicated, filtered view of inheritance hierarchies — exactly what this tool provides.

**Key recommendations:**

1. **Start with a prototype** — Build a minimal VS extension that can enumerate classes and their base classes using the DTE Code Model. Test this against the target codebase within the first week to validate the approach before investing in the full UI
2. **Use DTE Code Model as the primary analysis engine** — It's the simplest integration path and avoids external dependencies. Only escalate to libclang if DTE proves insufficient
3. **Design for swappable backends** — Abstract the code analysis behind an interface so the parsing strategy can evolve without rewriting the UI
4. **Target VS 2026 first** — Get it working on the required platform before investing in VS 2022 back-compatibility
5. **Test with real-world C++ code early and often** — The feasibility of the DTE approach depends on the specific C++ patterns used in the target codebase. Validate early

The main uncertainty is the completeness of the DTE Code Model for C++ virtual function analysis. This can be resolved in the first few days of prototyping. All other components (UI, navigation, filtering) are standard VS extension patterns with low technical risk.
