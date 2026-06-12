using System.Collections.Generic;

namespace VSIXProject.Analysis
{
    /// <summary>
    /// Abstraction over a backend that can answer inheritance/override questions for the
    /// Inheritance Navigator tool window.
    /// <para>
    /// The tool window can switch between implementations at runtime (see the data-source
    /// switch at the top of the panel). Today there are two implementations:
    /// </para>
    /// <list type="bullet">
    ///   <item><see cref="GraphifyDataSource"/> &#8212; reads a pre-built Graphify knowledge graph
    ///   (<c>graphify-out/graph.json</c>) if one is present in the solution.</item>
    ///   <item><see cref="LiveAnalysisDataSource"/> &#8212; placeholder for the in-process
    ///   ClangSharp/VCCodeModel C++ analysis described in the feasibility study.</item>
    /// </list>
    /// </summary>
    public interface IInheritanceDataSource
    {
        /// <summary>Short human readable name, e.g. "Graphify database".</summary>
        string DisplayName { get; }

        /// <summary>
        /// True when this source has data to serve (e.g. a Graphify database was found).
        /// The UI disables the corresponding switch position when a source is not available.
        /// </summary>
        bool IsAvailable { get; }

        /// <summary>
        /// One-line status describing the source, e.g. the database path and node count, or the
        /// reason the source is unavailable. Shown next to the switch at the top of the panel.
        /// </summary>
        string StatusText { get; }

        /// <summary>
        /// (Re)load the underlying data. Implementations should be safe to call from a background
        /// thread and must not throw &#8212; failures are reported through <see cref="IsAvailable"/>
        /// and <see cref="StatusText"/>.
        /// </summary>
        void Load();

        /// <summary>All classes known to the source (already filtered to project source where applicable).</summary>
        IReadOnlyList<CodeClass> GetClasses();

        /// <summary>Virtual / overridable methods declared or overridden by the given class.</summary>
        IReadOnlyList<CodeMethod> GetMethods(CodeClass owner);

        /// <summary>
        /// The chain of ancestor classes (most-derived base first) that declare/implement the
        /// selected method &#8212; powers the "Inherited From" section.
        /// </summary>
        IReadOnlyList<AncestorEntry> GetAncestors(CodeMethod method);

        /// <summary>
        /// The tree of derived classes that override the selected method &#8212; powers the
        /// "Derived Overrides" section. Returns the root nodes (direct overriders).
        /// </summary>
        IReadOnlyList<OverrideTreeNode> GetDerivedOverrides(CodeMethod method);
    }
}
