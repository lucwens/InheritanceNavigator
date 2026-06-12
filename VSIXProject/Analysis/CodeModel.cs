using System.Collections.Generic;

namespace VSIXProject.Analysis
{
    /// <summary>
    /// A C++ class / struct / interface discovered by an <see cref="IInheritanceDataSource"/>.
    /// </summary>
    public sealed class CodeClass
    {
        public CodeClass(string id, string name)
        {
            Id = id;
            Name = name;
            BaseClassIds = new List<string>();
            DerivedClassIds = new List<string>();
            MethodIds = new List<string>();
        }

        /// <summary>Stable identifier (node id from the data source).</summary>
        public string Id { get; }

        /// <summary>Simple class name shown in the UI.</summary>
        public string Name { get; }

        /// <summary>Folder/namespace style qualifier shown to the right of the name (may be null).</summary>
        public string Qualifier { get; set; }

        /// <summary>Absolute or solution-relative path to the file declaring the class (may be null).</summary>
        public string FilePath { get; set; }

        /// <summary>1-based line of the declaration (0 when unknown).</summary>
        public int Line { get; set; }

        /// <summary>Ids of the classes this class derives from directly.</summary>
        public List<string> BaseClassIds { get; }

        /// <summary>Ids of the classes that derive directly from this class.</summary>
        public List<string> DerivedClassIds { get; }

        /// <summary>Ids of the methods owned by this class.</summary>
        public List<string> MethodIds { get; }
    }

    /// <summary>
    /// A method / member function owned by a <see cref="CodeClass"/>.
    /// </summary>
    public sealed class CodeMethod
    {
        public CodeMethod(string id, string name)
        {
            Id = id;
            Name = name;
            OverriddenMethodIds = new List<string>();
            OverridingMethodIds = new List<string>();
        }

        public string Id { get; }

        /// <summary>Simple method name (used for override matching by name).</summary>
        public string Name { get; }

        /// <summary>Display signature, e.g. "Render(const Scene&amp;)" (falls back to <see cref="Name"/>).</summary>
        public string Signature { get; set; }

        /// <summary>Id of the owning class (may be null if ownership could not be resolved).</summary>
        public string OwnerClassId { get; set; }

        /// <summary>Path to the file containing the implementation (may be null).</summary>
        public string FilePath { get; set; }

        /// <summary>1-based line of the implementation/declaration (0 when unknown).</summary>
        public int Line { get; set; }

        /// <summary>True when the method is marked virtual / overridable.</summary>
        public bool IsVirtual { get; set; }

        /// <summary>True when the method overrides a base implementation.</summary>
        public bool IsOverride { get; set; }

        /// <summary>Ids of base-class methods this one overrides (explicit edges, if any).</summary>
        public List<string> OverriddenMethodIds { get; }

        /// <summary>Ids of derived-class methods that override this one (explicit edges, if any).</summary>
        public List<string> OverridingMethodIds { get; }

        public string DisplaySignature
        {
            get { return string.IsNullOrEmpty(Signature) ? Name : Signature; }
        }
    }

    /// <summary>
    /// A single row in the "Inherited From" ancestor list.
    /// </summary>
    public sealed class AncestorEntry
    {
        public AncestorEntry(string className, string methodSignature, string filePath, int line, bool isPureVirtual)
        {
            ClassName = className;
            MethodSignature = methodSignature;
            FilePath = filePath;
            Line = line;
            IsPureVirtual = isPureVirtual;
        }

        public string ClassName { get; }
        public string MethodSignature { get; }
        public string FilePath { get; }
        public int Line { get; }
        public bool IsPureVirtual { get; }

        /// <summary>True when an implementation file/line is available to navigate to.</summary>
        public bool CanNavigate
        {
            get { return !string.IsNullOrEmpty(FilePath); }
        }
    }

    /// <summary>
    /// A node in the "Derived Overrides" tree. Depth is expressed by the nesting of <see cref="Children"/>.
    /// </summary>
    public sealed class OverrideTreeNode
    {
        public OverrideTreeNode(string className, string methodSignature, string filePath, int line)
        {
            ClassName = className;
            MethodSignature = methodSignature;
            FilePath = filePath;
            Line = line;
            Children = new List<OverrideTreeNode>();
        }

        public string ClassName { get; }
        public string MethodSignature { get; }
        public string FilePath { get; }
        public int Line { get; }
        public List<OverrideTreeNode> Children { get; }

        public bool CanNavigate
        {
            get { return !string.IsNullOrEmpty(FilePath); }
        }
    }
}
