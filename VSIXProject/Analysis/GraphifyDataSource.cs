using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;

namespace VSIXProject.Analysis
{
    /// <summary>
    /// <see cref="IInheritanceDataSource"/> backed by a Graphify knowledge graph
    /// (<c>graphify-out/graph.json</c>, see https://github.com/safishamsi/graphify).
    /// <para>
    /// Graphify serialises a NetworkX graph; nodes are code symbols (classes, functions, &#8230;) and
    /// edges are relationships (containment, inheritance, calls, &#8230;). This source classifies the
    /// nodes/edges into an inheritance model and, because Graphify's tree-sitter pass does not reliably
    /// emit explicit C++ "overrides" edges, it <i>synthesises</i> the ancestor chain and derived-override
    /// tree from the inheritance edges plus method-name matching. Explicit override edges, when present,
    /// are honoured as well.
    /// </para>
    /// </summary>
    public sealed class GraphifyDataSource : IInheritanceDataSource
    {
        // Candidate locations of a Graphify database, relative to a search directory.
        private static readonly string[] RelativeDatabasePaths =
        {
            Path.Combine("graphify-out", "graph.json"),
            Path.Combine(".graphify", "graph.json"),
            Path.Combine("graphify", "graph.json"),
            "graph.json",
        };

        private readonly string _explicitPath;
        private readonly string _solutionDirectory;

        private readonly Dictionary<string, CodeClass> _classesById =
            new Dictionary<string, CodeClass>(StringComparer.Ordinal);
        private readonly Dictionary<string, CodeMethod> _methodsById =
            new Dictionary<string, CodeMethod>(StringComparer.Ordinal);
        private readonly Dictionary<string, List<CodeClass>> _classesByName =
            new Dictionary<string, List<CodeClass>>(StringComparer.Ordinal);

        private List<CodeClass> _sortedClasses = new List<CodeClass>();

        public GraphifyDataSource(string solutionDirectory, string explicitPath)
        {
            _solutionDirectory = solutionDirectory;
            _explicitPath = explicitPath;
        }

        public string DisplayName
        {
            get { return "Graphify database"; }
        }

        public bool IsAvailable { get; private set; }

        public string StatusText { get; private set; }

        /// <summary>Resolved path of the database that was loaded (null when none found).</summary>
        public string DatabasePath { get; private set; }

        /// <summary>
        /// Returns the path to a Graphify database discovered by walking up from
        /// <paramref name="startDirectory"/>, or null when none is found.
        /// </summary>
        public static string LocateDatabase(string startDirectory)
        {
            if (string.IsNullOrEmpty(startDirectory))
            {
                return null;
            }

            try
            {
                DirectoryInfo dir = new DirectoryInfo(startDirectory);
                int guard = 0;
                while (dir != null && guard < 8)
                {
                    foreach (string relative in RelativeDatabasePaths)
                    {
                        string candidate = Path.Combine(dir.FullName, relative);
                        if (File.Exists(candidate))
                        {
                            return candidate;
                        }
                    }

                    dir = dir.Parent;
                    guard++;
                }
            }
            catch
            {
                // ignore and report "not found"
            }

            return null;
        }

        public void Load()
        {
            Reset();

            string path = ResolvePath();
            DatabasePath = path;

            if (string.IsNullOrEmpty(path))
            {
                IsAvailable = false;
                StatusText = "No Graphify database found (looked for graphify-out/graph.json).";
                return;
            }

            GraphData graph = GraphJsonReader.ReadFile(path);
            if (graph == null)
            {
                IsAvailable = false;
                StatusText = "Could not read " + ShortPath(path) + ".";
                return;
            }

            Build(graph);

            IsAvailable = _sortedClasses.Count > 0;
            if (IsAvailable)
            {
                StatusText = string.Format(
                    CultureInfo.CurrentCulture,
                    "{0} — {1} classes, {2} methods",
                    ShortPath(path),
                    _sortedClasses.Count,
                    _methodsById.Count);
            }
            else
            {
                StatusText = "Loaded " + ShortPath(path) + " but found no classes in it.";
            }
        }

        public IReadOnlyList<CodeClass> GetClasses()
        {
            return _sortedClasses;
        }

        public IReadOnlyList<CodeMethod> GetMethods(CodeClass owner)
        {
            var result = new List<CodeMethod>();
            if (owner == null)
            {
                return result;
            }

            foreach (string methodId in owner.MethodIds)
            {
                CodeMethod method;
                if (_methodsById.TryGetValue(methodId, out method))
                {
                    result.Add(method);
                }
            }

            result.Sort((a, b) => string.Compare(a.DisplaySignature, b.DisplaySignature, StringComparison.OrdinalIgnoreCase));
            return result;
        }

        public IReadOnlyList<AncestorEntry> GetAncestors(CodeMethod method)
        {
            var result = new List<AncestorEntry>();
            if (method == null || method.OwnerClassId == null)
            {
                return result;
            }

            CodeClass owner;
            if (!_classesById.TryGetValue(method.OwnerClassId, out owner))
            {
                return result;
            }

            // Breadth-first walk up the base chain; closest base classes first.
            var visited = new HashSet<string>(StringComparer.Ordinal);
            var queue = new Queue<CodeClass>();
            EnqueueBases(owner, queue, visited);

            while (queue.Count > 0)
            {
                CodeClass ancestor = queue.Dequeue();
                CodeMethod match = FindMethodByName(ancestor, method.Name);
                if (match != null)
                {
                    result.Add(new AncestorEntry(
                        ancestor.Name,
                        match.DisplaySignature,
                        match.FilePath,
                        match.Line,
                        IsPureVirtual(match)));
                }

                EnqueueBases(ancestor, queue, visited);
            }

            return result;
        }

        public IReadOnlyList<OverrideTreeNode> GetDerivedOverrides(CodeMethod method)
        {
            var roots = new List<OverrideTreeNode>();
            if (method == null || method.OwnerClassId == null)
            {
                return roots;
            }

            CodeClass owner;
            if (!_classesById.TryGetValue(method.OwnerClassId, out owner))
            {
                return roots;
            }

            var visited = new HashSet<string>(StringComparer.Ordinal);
            visited.Add(owner.Id);
            foreach (CodeClass child in DerivedClasses(owner))
            {
                OverrideTreeNode node = BuildOverrideNode(child, method.Name, visited);
                if (node != null)
                {
                    roots.Add(node);
                }
            }

            roots.Sort((a, b) => string.Compare(a.ClassName, b.ClassName, StringComparison.OrdinalIgnoreCase));
            return roots;
        }

        // -- build -------------------------------------------------------------------------------

        private void Reset()
        {
            _classesById.Clear();
            _methodsById.Clear();
            _classesByName.Clear();
            _sortedClasses = new List<CodeClass>();
            IsAvailable = false;
            StatusText = null;
            DatabasePath = null;
        }

        private void Build(GraphData graph)
        {
            // 1) Classify nodes into classes and methods.
            foreach (GraphNode node in graph.Nodes)
            {
                if (RelationshipVocabulary.IsClassType(node.Type))
                {
                    if (!_classesById.ContainsKey(node.Id))
                    {
                        var c = new CodeClass(node.Id, CleanName(node.Label, node.Id));
                        c.FilePath = node.SourceFile;
                        c.Line = node.Line;
                        c.Qualifier = DeriveQualifier(node.SourceFile);
                        _classesById[node.Id] = c;
                        IndexByName(c);
                    }
                }
                else if (RelationshipVocabulary.IsMethodType(node.Type))
                {
                    if (!_methodsById.ContainsKey(node.Id))
                    {
                        var m = new CodeMethod(node.Id, MethodName(node));
                        m.Signature = MethodSignature(node);
                        m.FilePath = node.SourceFile;
                        m.Line = node.Line;
                        m.IsVirtual = LooksVirtual(node);
                        _methodsById[node.Id] = m;
                    }
                }
            }

            // 2) Apply edges: containment (owner), inheritance, explicit overrides.
            foreach (GraphEdge edge in graph.Edges)
            {
                RelationshipKind kind = RelationshipVocabulary.Classify(edge.Type);
                switch (kind)
                {
                    case RelationshipKind.Containment:
                        ApplyContainment(edge.Source, edge.Target);
                        break;
                    case RelationshipKind.InheritsDerivedToBase:
                        ApplyInheritance(edge.Source, edge.Target);
                        break;
                    case RelationshipKind.InheritsBaseToDerived:
                        ApplyInheritance(edge.Target, edge.Source);
                        break;
                    case RelationshipKind.OverrideChildToParent:
                        ApplyOverride(edge.Source, edge.Target);
                        break;
                    case RelationshipKind.OverrideParentToChild:
                        ApplyOverride(edge.Target, edge.Source);
                        break;
                }
            }

            // 3) Best-effort ownership for methods that no containment edge resolved, using
            //    qualified names such as "Namespace::Class::method" or "Class.method".
            foreach (CodeMethod method in _methodsById.Values)
            {
                if (method.OwnerClassId == null)
                {
                    TryResolveOwnerByName(method);
                }
            }

            // 4) Mark methods that have a same-named declaration in a base class as overrides.
            MarkOverridesByName();

            _sortedClasses = _classesById.Values.ToList();
            _sortedClasses.Sort((a, b) => string.Compare(a.Name, b.Name, StringComparison.OrdinalIgnoreCase));
        }

        private void ApplyContainment(string sourceId, string targetId)
        {
            // Either endpoint may be the class and the other the method.
            if (_classesById.ContainsKey(sourceId) && _methodsById.ContainsKey(targetId))
            {
                AssignOwner(_methodsById[targetId], _classesById[sourceId]);
            }
            else if (_classesById.ContainsKey(targetId) && _methodsById.ContainsKey(sourceId))
            {
                AssignOwner(_methodsById[sourceId], _classesById[targetId]);
            }
        }

        private void AssignOwner(CodeMethod method, CodeClass owner)
        {
            if (method.OwnerClassId != null)
            {
                return;
            }

            method.OwnerClassId = owner.Id;
            if (!owner.MethodIds.Contains(method.Id))
            {
                owner.MethodIds.Add(method.Id);
            }
        }

        private void ApplyInheritance(string derivedId, string baseId)
        {
            CodeClass derived, baseClass;
            if (!_classesById.TryGetValue(derivedId, out derived) ||
                !_classesById.TryGetValue(baseId, out baseClass))
            {
                return;
            }

            if (derived.Id == baseClass.Id)
            {
                return;
            }

            if (!derived.BaseClassIds.Contains(baseClass.Id))
            {
                derived.BaseClassIds.Add(baseClass.Id);
            }

            if (!baseClass.DerivedClassIds.Contains(derived.Id))
            {
                baseClass.DerivedClassIds.Add(derived.Id);
            }
        }

        private void ApplyOverride(string overridingId, string overriddenId)
        {
            CodeMethod overriding, overridden;
            if (!_methodsById.TryGetValue(overridingId, out overriding) ||
                !_methodsById.TryGetValue(overriddenId, out overridden))
            {
                return;
            }

            overriding.IsOverride = true;
            if (!overriding.OverriddenMethodIds.Contains(overridden.Id))
            {
                overriding.OverriddenMethodIds.Add(overridden.Id);
            }

            if (!overridden.OverridingMethodIds.Contains(overriding.Id))
            {
                overridden.OverridingMethodIds.Add(overriding.Id);
            }
        }

        private void TryResolveOwnerByName(CodeMethod method)
        {
            string qualified = method.Signature ?? method.Name;
            if (string.IsNullOrEmpty(qualified))
            {
                return;
            }

            string ownerName = ExtractOwnerName(qualified);
            if (ownerName == null)
            {
                return;
            }

            List<CodeClass> candidates;
            if (_classesByName.TryGetValue(ownerName, out candidates) && candidates.Count > 0)
            {
                AssignOwner(method, candidates[0]);
            }
        }

        private void MarkOverridesByName()
        {
            foreach (CodeClass cls in _classesById.Values)
            {
                if (cls.BaseClassIds.Count == 0)
                {
                    continue;
                }

                foreach (string methodId in cls.MethodIds)
                {
                    CodeMethod method;
                    if (!_methodsById.TryGetValue(methodId, out method) || method.IsOverride)
                    {
                        continue;
                    }

                    if (HasAncestorMethod(cls, method.Name))
                    {
                        method.IsOverride = true;
                    }
                }
            }
        }

        private bool HasAncestorMethod(CodeClass cls, string methodName)
        {
            var visited = new HashSet<string>(StringComparer.Ordinal);
            var queue = new Queue<CodeClass>();
            EnqueueBases(cls, queue, visited);

            while (queue.Count > 0)
            {
                CodeClass ancestor = queue.Dequeue();
                if (FindMethodByName(ancestor, methodName) != null)
                {
                    return true;
                }

                EnqueueBases(ancestor, queue, visited);
            }

            return false;
        }

        private OverrideTreeNode BuildOverrideNode(CodeClass cls, string methodName, HashSet<string> visited)
        {
            if (cls == null || visited.Contains(cls.Id))
            {
                return null;
            }

            visited.Add(cls.Id);

            CodeMethod overriding = FindMethodByName(cls, methodName);

            var childNodes = new List<OverrideTreeNode>();
            foreach (CodeClass child in DerivedClasses(cls))
            {
                OverrideTreeNode childNode = BuildOverrideNode(child, methodName, visited);
                if (childNode != null)
                {
                    childNodes.Add(childNode);
                }
            }

            // Prune classes that neither override the method nor have a descendant that does.
            if (overriding == null && childNodes.Count == 0)
            {
                return null;
            }

            if (overriding == null)
            {
                // Non-overriding intermediate: lift its overriding descendants up to this level.
                // Returning a synthetic node keeps the hierarchy readable; callers can flatten if desired.
                var passthrough = new OverrideTreeNode(cls.Name, null, null, 0);
                passthrough.Children.AddRange(childNodes);
                return passthrough;
            }

            var node = new OverrideTreeNode(cls.Name, overriding.DisplaySignature, overriding.FilePath, overriding.Line);
            childNodes.Sort((a, b) => string.Compare(a.ClassName, b.ClassName, StringComparison.OrdinalIgnoreCase));
            node.Children.AddRange(childNodes);
            return node;
        }

        // -- helpers -----------------------------------------------------------------------------

        private void EnqueueBases(CodeClass cls, Queue<CodeClass> queue, HashSet<string> visited)
        {
            foreach (string baseId in cls.BaseClassIds)
            {
                CodeClass baseClass;
                if (_classesById.TryGetValue(baseId, out baseClass) && visited.Add(baseClass.Id))
                {
                    queue.Enqueue(baseClass);
                }
            }
        }

        private IEnumerable<CodeClass> DerivedClasses(CodeClass cls)
        {
            foreach (string derivedId in cls.DerivedClassIds)
            {
                CodeClass derived;
                if (_classesById.TryGetValue(derivedId, out derived))
                {
                    yield return derived;
                }
            }
        }

        private CodeMethod FindMethodByName(CodeClass cls, string methodName)
        {
            foreach (string methodId in cls.MethodIds)
            {
                CodeMethod method;
                if (_methodsById.TryGetValue(methodId, out method) &&
                    string.Equals(method.Name, methodName, StringComparison.Ordinal))
                {
                    return method;
                }
            }

            return null;
        }

        private void IndexByName(CodeClass c)
        {
            List<CodeClass> list;
            if (!_classesByName.TryGetValue(c.Name, out list))
            {
                list = new List<CodeClass>();
                _classesByName[c.Name] = list;
            }

            list.Add(c);
        }

        private string ResolvePath()
        {
            if (!string.IsNullOrEmpty(_explicitPath) && File.Exists(_explicitPath))
            {
                return _explicitPath;
            }

            return LocateDatabase(_solutionDirectory);
        }

        private static bool IsPureVirtual(CodeMethod method)
        {
            string sig = method.Signature;
            if (!string.IsNullOrEmpty(sig) && sig.Replace(" ", string.Empty).IndexOf("=0", StringComparison.Ordinal) >= 0)
            {
                return true;
            }

            return false;
        }

        private static bool LooksVirtual(GraphNode node)
        {
            string label = (node.Label ?? string.Empty).ToLowerInvariant();
            return label.IndexOf("virtual", StringComparison.Ordinal) >= 0
                || label.IndexOf("override", StringComparison.Ordinal) >= 0;
        }

        private static string MethodName(GraphNode node)
        {
            // Strip any signature tail and owner qualifier to get the simple name.
            string name = StripSignatureTail(CleanName(node.Label, node.Id));

            string owner, simple;
            SplitQualified(name, out owner, out simple);
            return simple.Trim();
        }

        private static string MethodSignature(GraphNode node)
        {
            object value;
            if (node.Raw != null)
            {
                foreach (string key in new[] { "signature", "sig", "display", "full_name", "qualified_name" })
                {
                    if (node.Raw.TryGetValue(key, out value) && value is string && ((string)value).Length > 0)
                    {
                        return (string)value;
                    }
                }
            }

            return CleanName(node.Label, node.Id);
        }

        private static string ExtractOwnerName(string qualified)
        {
            string name = StripSignatureTail(qualified);

            string owner, simple;
            SplitQualified(name, out owner, out simple);
            if (string.IsNullOrEmpty(owner))
            {
                return null;
            }

            // The owner may itself be qualified (e.g. "Namespace::Class") — take the last segment.
            string outerOwner, immediate;
            SplitQualified(owner, out outerOwner, out immediate);
            immediate = (immediate ?? owner).Trim();
            return immediate.Length > 0 ? immediate : null;
        }

        private static string StripSignatureTail(string value)
        {
            if (string.IsNullOrEmpty(value))
            {
                return string.Empty;
            }

            int paren = value.IndexOf('(');
            string name = paren >= 0 ? value.Substring(0, paren) : value;
            return name.Trim();
        }

        /// <summary>Splits "Namespace::Class::method" or "Class.method" into owner and simple name.</summary>
        private static void SplitQualified(string name, out string owner, out string simple)
        {
            owner = null;
            simple = name ?? string.Empty;
            if (string.IsNullOrEmpty(name))
            {
                return;
            }

            int colons = name.LastIndexOf("::", StringComparison.Ordinal);
            if (colons >= 0)
            {
                owner = name.Substring(0, colons);
                simple = name.Substring(colons + 2);
                return;
            }

            int dot = name.LastIndexOf('.');
            if (dot >= 0)
            {
                owner = name.Substring(0, dot);
                simple = name.Substring(dot + 1);
            }
        }

        private static string CleanName(string label, string id)
        {
            if (!string.IsNullOrEmpty(label))
            {
                return label;
            }

            return id ?? string.Empty;
        }

        private static string DeriveQualifier(string sourceFile)
        {
            if (string.IsNullOrEmpty(sourceFile))
            {
                return null;
            }

            try
            {
                string dir = Path.GetDirectoryName(sourceFile);
                if (string.IsNullOrEmpty(dir))
                {
                    return null;
                }

                string leaf = new DirectoryInfo(dir).Name;
                return string.IsNullOrEmpty(leaf) ? null : leaf;
            }
            catch
            {
                return null;
            }
        }

        private static string ShortPath(string path)
        {
            if (string.IsNullOrEmpty(path))
            {
                return string.Empty;
            }

            try
            {
                var info = new FileInfo(path);
                string parent = info.Directory != null ? info.Directory.Name : string.Empty;
                var sb = new StringBuilder();
                if (parent.Length > 0)
                {
                    sb.Append(parent).Append(Path.DirectorySeparatorChar);
                }

                sb.Append(info.Name);
                return sb.ToString();
            }
            catch
            {
                return path;
            }
        }
    }
}
