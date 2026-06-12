using System.Collections.Generic;

namespace VSIXProject.Analysis
{
    /// <summary>
    /// Placeholder for the in-process C++ analysis backend (ClangSharp / VCCodeModel) described in
    /// <c>Doc/Feasibility.md</c>. It is the "other side" of the data-source switch: selectable so the
    /// UI and architecture are complete, but not yet implemented.
    /// <para>
    /// When the live analyzer is built it only has to implement <see cref="IInheritanceDataSource"/>;
    /// nothing in the tool window needs to change.
    /// </para>
    /// </summary>
    public sealed class LiveAnalysisDataSource : IInheritanceDataSource
    {
        private static readonly IReadOnlyList<CodeClass> NoClasses = new List<CodeClass>();
        private static readonly IReadOnlyList<CodeMethod> NoMethods = new List<CodeMethod>();
        private static readonly IReadOnlyList<AncestorEntry> NoAncestors = new List<AncestorEntry>();
        private static readonly IReadOnlyList<OverrideTreeNode> NoOverrides = new List<OverrideTreeNode>();

        public string DisplayName
        {
            get { return "Live C++ analysis"; }
        }

        // Reported as unavailable so the UI prefers Graphify and explains why this side is empty.
        public bool IsAvailable
        {
            get { return false; }
        }

        public string StatusText
        {
            get { return "Live C++ analysis (ClangSharp) is not implemented yet — use a Graphify database."; }
        }

        public void Load()
        {
            // Nothing to load yet.
        }

        public IReadOnlyList<CodeClass> GetClasses()
        {
            return NoClasses;
        }

        public IReadOnlyList<CodeMethod> GetMethods(CodeClass owner)
        {
            return NoMethods;
        }

        public IReadOnlyList<AncestorEntry> GetAncestors(CodeMethod method)
        {
            return NoAncestors;
        }

        public IReadOnlyList<OverrideTreeNode> GetDerivedOverrides(CodeMethod method)
        {
            return NoOverrides;
        }
    }
}
