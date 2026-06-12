using System;
using System.Collections.Generic;

namespace VSIXProject.Analysis
{
    /// <summary>
    /// Coordinates the available data sources and the "use Graphify database" switch for the tool
    /// window. UI-agnostic so it can be unit tested without Visual Studio.
    /// </summary>
    public sealed class NavigatorController
    {
        private readonly GraphifyDataSource _graphify;
        private readonly LiveAnalysisDataSource _live;

        private IInheritanceDataSource _active;
        private bool _useGraphify;

        public NavigatorController(string solutionDirectory, string explicitGraphifyPath)
        {
            _graphify = new GraphifyDataSource(solutionDirectory, explicitGraphifyPath);
            _live = new LiveAnalysisDataSource();
            _active = _live;
        }

        /// <summary>Raised after <see cref="Reload"/> or a switch change so the UI can repaint.</summary>
        public event EventHandler SourceChanged;

        /// <summary>True when a Graphify database was found and contains classes.</summary>
        public bool GraphifyAvailable
        {
            get { return _graphify.IsAvailable; }
        }

        /// <summary>State of the switch at the top of the panel.</summary>
        public bool UseGraphify
        {
            get { return _useGraphify; }
            set
            {
                bool effective = value && _graphify.IsAvailable;
                if (effective == _useGraphify && _active != null)
                {
                    return;
                }

                _useGraphify = effective;
                _active = effective ? (IInheritanceDataSource)_graphify : _live;
                RaiseSourceChanged();
            }
        }

        public IInheritanceDataSource ActiveSource
        {
            get { return _active; }
        }

        public string GraphifyStatus
        {
            get { return _graphify.StatusText; }
        }

        public string ActiveStatus
        {
            get { return _active != null ? _active.StatusText : string.Empty; }
        }

        /// <summary>
        /// Loads (or reloads) the Graphify database and selects the best default source. Performs file
        /// IO, so call it from a background thread.
        /// </summary>
        public void Reload()
        {
            _graphify.Load();
            _live.Load();

            // Default to Graphify whenever it is available.
            _useGraphify = _graphify.IsAvailable;
            _active = _useGraphify ? (IInheritanceDataSource)_graphify : _live;
            RaiseSourceChanged();
        }

        public IReadOnlyList<CodeClass> GetClasses(string filter)
        {
            var result = new List<CodeClass>();
            string[] fragments = SplitFragments(filter);
            foreach (CodeClass c in _active.GetClasses())
            {
                if (MatchesAll(c.Name, fragments))
                {
                    result.Add(c);
                }
            }

            return result;
        }

        public IReadOnlyList<CodeMethod> GetMethods(CodeClass owner, string filter)
        {
            var result = new List<CodeMethod>();
            if (owner == null)
            {
                return result;
            }

            string[] fragments = SplitFragments(filter);
            foreach (CodeMethod m in _active.GetMethods(owner))
            {
                if (MatchesAll(m.DisplaySignature, fragments))
                {
                    result.Add(m);
                }
            }

            return result;
        }

        public IReadOnlyList<AncestorEntry> GetAncestors(CodeMethod method)
        {
            return _active.GetAncestors(method);
        }

        public IReadOnlyList<OverrideTreeNode> GetDerivedOverrides(CodeMethod method)
        {
            return _active.GetDerivedOverrides(method);
        }

        private void RaiseSourceChanged()
        {
            EventHandler handler = SourceChanged;
            if (handler != null)
            {
                handler(this, EventArgs.Empty);
            }
        }

        private static string[] SplitFragments(string filter)
        {
            if (string.IsNullOrWhiteSpace(filter))
            {
                return new string[0];
            }

            return filter.Split(new[] { ' ', '\t' }, StringSplitOptions.RemoveEmptyEntries);
        }

        private static bool MatchesAll(string text, string[] fragments)
        {
            if (fragments.Length == 0)
            {
                return true;
            }

            if (string.IsNullOrEmpty(text))
            {
                return false;
            }

            foreach (string fragment in fragments)
            {
                if (text.IndexOf(fragment, StringComparison.OrdinalIgnoreCase) < 0)
                {
                    return false;
                }
            }

            return true;
        }
    }
}
