# Graphify Integration

The Inheritance Navigator can draw its data from a **Graphify** knowledge graph instead of
analysing C++ live. A switch at the very top of the tool window — **“Use Graphify database”** —
selects between the two. When a Graphify database is found in the solution it is detected
automatically, preferred, and read; the switch lets you fall back to the (not-yet-implemented)
live C++ analysis.

Graphify is the open-source “turn any codebase into a queryable knowledge graph” tool:
<https://github.com/safishamsi/graphify>.

## How a database is detected

When the tool window loads (and on every **Refresh**), it asks Visual Studio for the open
solution directory and walks upward looking for the first of:

| Candidate (relative to each directory) |
| -------------------------------------- |
| `graphify-out/graph.json`              |
| `.graphify/graph.json`                 |
| `graphify/graph.json`                  |
| `graph.json`                           |

`graphify-out/graph.json` is Graphify’s default output location. If none is found, the switch is
disabled and the status line explains why.

## What is read from `graph.json`

Graphify serialises a NetworkX graph with `networkx.node_link_data`, producing:

```jsonc
{
  "directed": true,
  "nodes": [ { "id": "...", "type": "class", "source_file": "...", "line": 42, ... }, ... ],
  "links": [ { "source": "...", "target": "...", "type": "CONTAINS", ... }, ... ]
}
```

The reader (`Analysis/GraphJsonReader.cs`) is deliberately tolerant: for every value it tries a
list of candidate keys (e.g. a node label may be under `label`, `name`, `title`, `norm_label`,
or fall back to `id`; a line may be under `line`, `lineno`, `start_line`, …) because the exact
field names vary between Graphify versions and languages.

### Node classification

* **Classes** — nodes whose `type` contains `class`, `struct`, `interface`, `trait`, `record`, …
* **Methods** — nodes whose `type` contains `method`, `function`, `member`, `ctor`, `operator`, …

### Edge classification

Relationship labels are normalised (lower-cased, punctuation stripped) and matched against the
vocabulary in `Analysis/RelationshipVocabulary.cs`:

| Concept                          | Example labels matched                                             |
| -------------------------------- | ----------------------------------------------------------------- |
| Containment (class → method)     | `CONTAINS`, `DEFINES`, `DECLARES`, `HAS_METHOD`, `MEMBER` …        |
| Inheritance (derived → base)     | `EXTENDS`, `INHERITS`, `INHERITS_FROM`, `SUBCLASS_OF`, `DERIVES` … |
| Inheritance (base → derived)     | `BASE_OF`, `SUPERCLASS_OF`, `PARENT_OF`, `INHERITED_BY` …          |
| Override (child → parent method) | `OVERRIDES`, `IMPLEMENTS`, `REDEFINES` …                           |
| Override (parent → child method) | `OVERRIDDEN_BY`, `IMPLEMENTED_BY` …                                |

**This vocabulary is the single place to adjust** if a particular database uses different labels.

### Synthesised override relationships

Graphify’s tree-sitter pass extracts classes, functions, imports and call graphs, but it does
**not** reliably emit explicit C++ “overrides” edges. So the two override views are derived from
inheritance edges + method ownership + name matching:

* **Inherited From** — walks the selected class’s base chain upward (breadth-first, closest base
  first) and lists every ancestor that declares a method with the same name.
* **Derived Overrides** — walks the descendants and builds a tree of those that declare a
  same-named method, nesting each overrider under its nearest overriding ancestor. Non-overriding
  intermediate classes are pruned but still traversed so deeper overrides are not lost.

Explicit `OVERRIDES` edges, when present, are honoured in addition to the synthesised ones.

## Limitations / notes

* Method ownership comes from containment edges; where those are missing, the owner is inferred
  from qualified names such as `Namespace::Class::method` or `Class.method`.
* “Virtual” vs “override” tags are best-effort (from explicit override edges, name-based override
  detection, or a `virtual`/`override` hint in the label). Without semantic data the tool cannot
  guarantee a function is virtual.
* Large graphs are read on a background thread; the class/function lists cap at 1000 visible rows.
* The live C++ (ClangSharp / VCCodeModel) backend described in `Doc/Feasibility.md` is the other
  side of the switch and is currently a stub (`Analysis/LiveAnalysisDataSource.cs`). Implementing
  it only requires providing another `IInheritanceDataSource`; no UI changes are needed.
