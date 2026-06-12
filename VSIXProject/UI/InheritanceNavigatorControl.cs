using System;
using System.Collections.Generic;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using Microsoft.VisualStudio;
using Microsoft.VisualStudio.Shell;
using Microsoft.VisualStudio.Shell.Interop;
using VSIXProject.Analysis;
using IServiceProvider = System.IServiceProvider;

namespace VSIXProject.UI
{
    /// <summary>
    /// The Inheritance Navigator tool-window panel. The entire UI is built in code (no XAML) so the
    /// project needs no WPF markup compiler step. The headline feature is the data-source switch at the
    /// very top: when a Graphify database is present it is detected, preferred, and read; the switch lets
    /// the user fall back to (the not-yet-implemented) live C++ analysis.
    /// </summary>
    public sealed class InheritanceNavigatorControl : UserControl
    {
        private const int MaxRows = 1000;

        private NavigatorController _controller;
        private string _solutionDirectory;

        private CheckBox _graphifySwitch;
        private TextBlock _statusText;

        private StackPanel _folderPanel;
        private readonly HashSet<string> _enabledFolders = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        private TextBox _classSearch;
        private ListBox _classList;
        private TextBlock _classCount;

        private TextBox _functionSearch;
        private ListBox _functionList;
        private TextBlock _functionContext;

        private ListBox _ancestorList;
        private TextBlock _ancestorContext;

        private TreeView _derivedTree;
        private TextBlock _derivedContext;

        private CodeClass _selectedClass;
        private CodeMethod _selectedMethod;

        public InheritanceNavigatorControl()
        {
            Content = BuildLayout();
            this.SetResourceReference(BackgroundProperty, VsBrushes.ToolWindowBackgroundKey);
            this.SetResourceReference(ForegroundProperty, VsBrushes.ToolWindowTextKey);
            Loaded += OnLoaded;
        }

        private void OnLoaded(object sender, RoutedEventArgs e)
        {
            BeginRefresh();
        }

        // -- layout ------------------------------------------------------------------------------

        private UIElement BuildLayout()
        {
            var root = new DockPanel { LastChildFill = true };

            root.Children.Add(DockTop(BuildTopBar()));

            var grid = new Grid();
            grid.RowDefinitions.Add(StarRow(1));    // Source Folders
            grid.RowDefinitions.Add(StarRow(2.2));  // Class
            grid.RowDefinitions.Add(StarRow(2));    // Virtual Functions
            grid.RowDefinitions.Add(StarRow(1.6));  // Inherited From
            grid.RowDefinitions.Add(StarRow(2.4));  // Derived Overrides

            AddRow(grid, 0, BuildFolderSection());
            AddRow(grid, 1, BuildClassSection());
            AddRow(grid, 2, BuildFunctionSection());
            AddRow(grid, 3, BuildAncestorSection());
            AddRow(grid, 4, BuildDerivedSection());

            root.Children.Add(grid);
            return root;
        }

        private UIElement BuildTopBar()
        {
            var panel = new StackPanel { Orientation = Orientation.Vertical, Margin = new Thickness(6, 6, 6, 4) };

            var row = new DockPanel { LastChildFill = true };

            var refresh = new Button
            {
                Content = "Refresh",
                Padding = new Thickness(8, 1, 8, 1),
                Margin = new Thickness(8, 0, 0, 0),
            };
            refresh.Click += (s, e) => BeginRefresh();
            DockPanel.SetDock(refresh, Dock.Right);
            row.Children.Add(refresh);

            _graphifySwitch = new CheckBox
            {
                Content = "Use Graphify database",
                VerticalAlignment = VerticalAlignment.Center,
                IsEnabled = false,
            };
            _graphifySwitch.Click += GraphifySwitch_Click;
            row.Children.Add(_graphifySwitch);

            panel.Children.Add(row);

            _statusText = new TextBlock
            {
                Margin = new Thickness(0, 4, 0, 0),
                TextWrapping = TextWrapping.Wrap,
                Opacity = 0.75,
                Text = "Looking for a Graphify database…",
            };
            panel.Children.Add(_statusText);

            var border = new Border
            {
                Child = panel,
                BorderThickness = new Thickness(0, 0, 0, 1),
            };
            border.SetResourceReference(Border.BorderBrushProperty, VsBrushes.ToolWindowBorderKey);
            return border;
        }

        private UIElement BuildFolderSection()
        {
            var header = SectionHeader("Source Folders", out _);

            var buttons = new StackPanel { Orientation = Orientation.Horizontal };
            var all = new Button { Content = "All", Padding = new Thickness(6, 0, 6, 0), Margin = new Thickness(0, 0, 4, 0) };
            var none = new Button { Content = "None", Padding = new Thickness(6, 0, 6, 0) };
            all.Click += (s, e) => SetAllFolders(true);
            none.Click += (s, e) => SetAllFolders(false);
            buttons.Children.Add(all);
            buttons.Children.Add(none);
            DockPanel.SetDock(buttons, Dock.Right);
            ((DockPanel)header).Children.Insert(0, buttons);

            _folderPanel = new StackPanel { Orientation = Orientation.Vertical, Margin = new Thickness(6, 2, 6, 2) };
            var scroller = new ScrollViewer
            {
                Content = _folderPanel,
                VerticalScrollBarVisibility = ScrollBarVisibility.Auto,
            };

            return Section(header, scroller);
        }

        private UIElement BuildClassSection()
        {
            var header = SectionHeader("Class", out _classCount);

            _classSearch = MakeSearchBox("Type to filter classes…");
            _classSearch.TextChanged += (s, e) => RefreshClassList();

            _classList = MakeListBox();
            _classList.SelectionChanged += ClassList_SelectionChanged;
            _classList.MouseDoubleClick += (s, e) => NavigateFromList(_classList);

            return Section(header, StackVertical(_classSearch, _classList));
        }

        private UIElement BuildFunctionSection()
        {
            var header = SectionHeader("Virtual Functions", out _functionContext);

            _functionSearch = MakeSearchBox("Type to filter functions…");
            _functionSearch.TextChanged += (s, e) => RefreshFunctionList();

            _functionList = MakeListBox();
            _functionList.SelectionChanged += FunctionList_SelectionChanged;
            _functionList.MouseDoubleClick += (s, e) => NavigateFromList(_functionList);

            return Section(header, StackVertical(_functionSearch, _functionList));
        }

        private UIElement BuildAncestorSection()
        {
            var header = SectionHeader("Inherited From", out _ancestorContext);

            _ancestorList = MakeListBox();
            _ancestorList.MouseDoubleClick += (s, e) => NavigateFromList(_ancestorList);

            return Section(header, _ancestorList);
        }

        private UIElement BuildDerivedSection()
        {
            var header = SectionHeader("Derived Overrides", out _derivedContext);

            _derivedTree = new TreeView { BorderThickness = new Thickness(0) };
            ApplyThemed(_derivedTree);
            _derivedTree.MouseDoubleClick += DerivedTree_MouseDoubleClick;

            return Section(header, _derivedTree);
        }

        // -- data flow ---------------------------------------------------------------------------

        private void BeginRefresh()
        {
            _ = ThreadHelper.JoinableTaskFactory.RunAsync(async () =>
            {
                await ThreadHelper.JoinableTaskFactory.SwitchToMainThreadAsync();
                RebuildController();
                SetStatus("Loading…");
                await System.Threading.Tasks.Task.Run(() => _controller.Reload());
            });
        }

        private void RebuildController()
        {
            ThreadHelper.ThrowIfNotOnUIThread();

            if (_controller != null)
            {
                _controller.SourceChanged -= Controller_SourceChanged;
            }

            _solutionDirectory = GetSolutionDirectory();
            _controller = new NavigatorController(_solutionDirectory, null);
            _controller.SourceChanged += Controller_SourceChanged;
        }

        private void Controller_SourceChanged(object sender, EventArgs e)
        {
            if (!Dispatcher.CheckAccess())
            {
                Dispatcher.BeginInvoke(new Action(RepaintAll));
                return;
            }

            RepaintAll();
        }

        private void RepaintAll()
        {
            _graphifySwitch.IsEnabled = _controller.GraphifyAvailable;
            _graphifySwitch.IsChecked = _controller.UseGraphify;
            SetStatus(_controller.ActiveStatus);

            RebuildFolderList();

            _selectedClass = null;
            _selectedMethod = null;
            RefreshClassList();
            ClearFunctions();
            ClearAncestorsAndDerived();
        }

        private void GraphifySwitch_Click(object sender, RoutedEventArgs e)
        {
            _controller.UseGraphify = _graphifySwitch.IsChecked == true;
        }

        // -- folders -----------------------------------------------------------------------------

        private void RebuildFolderList()
        {
            _folderPanel.Children.Clear();

            var folders = new SortedSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (CodeClass c in _controller.ActiveSource.GetClasses())
            {
                folders.Add(FolderKey(c));
            }

            _enabledFolders.Clear();
            foreach (string folder in folders)
            {
                _enabledFolders.Add(folder);

                var box = new CheckBox
                {
                    Content = ShortenFolder(folder),
                    Tag = folder,
                    IsChecked = true,
                    Margin = new Thickness(0, 1, 0, 1),
                    ToolTip = folder,
                };
                box.Click += Folder_Click;
                _folderPanel.Children.Add(box);
            }

            if (folders.Count == 0)
            {
                _folderPanel.Children.Add(new TextBlock { Text = "(no source folders)", Opacity = 0.6 });
            }
        }

        private void Folder_Click(object sender, RoutedEventArgs e)
        {
            var box = (CheckBox)sender;
            string folder = (string)box.Tag;
            if (box.IsChecked == true)
            {
                _enabledFolders.Add(folder);
            }
            else
            {
                _enabledFolders.Remove(folder);
            }

            RefreshClassList();
        }

        private void SetAllFolders(bool enabled)
        {
            foreach (object child in _folderPanel.Children)
            {
                var box = child as CheckBox;
                if (box == null)
                {
                    continue;
                }

                box.IsChecked = enabled;
                string folder = (string)box.Tag;
                if (enabled)
                {
                    _enabledFolders.Add(folder);
                }
                else
                {
                    _enabledFolders.Remove(folder);
                }
            }

            RefreshClassList();
        }

        // -- class / function lists --------------------------------------------------------------

        private void RefreshClassList()
        {
            _classList.Items.Clear();

            int shown = 0;
            int total = 0;
            foreach (CodeClass c in _controller.GetClasses(_classSearch.Text))
            {
                total++;
                if (!_enabledFolders.Contains(FolderKey(c)))
                {
                    continue;
                }

                if (shown < MaxRows)
                {
                    _classList.Items.Add(MakeRow(c.Name, c.Qualifier, c, false));
                }

                shown++;
            }

            _classCount.Text = shown > MaxRows
                ? string.Format("showing {0} of {1}", MaxRows, shown)
                : shown.ToString();

            ClearFunctions();
            ClearAncestorsAndDerived();
        }

        private void ClassList_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            _selectedClass = SelectedTag(_classList) as CodeClass;
            RefreshFunctionList();
            ClearAncestorsAndDerived();
        }

        private void RefreshFunctionList()
        {
            _functionList.Items.Clear();
            _functionContext.Text = _selectedClass != null ? _selectedClass.Name : string.Empty;

            if (_selectedClass == null)
            {
                return;
            }

            foreach (CodeMethod m in _controller.GetMethods(_selectedClass, _functionSearch.Text))
            {
                string tag = m.IsOverride ? "override" : (m.IsVirtual ? "virtual" : null);
                _functionList.Items.Add(MakeRow(m.DisplaySignature, tag, m, false));
            }
        }

        private void FunctionList_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            _selectedMethod = SelectedTag(_functionList) as CodeMethod;
            RefreshAncestors();
            RefreshDerived();
        }

        private void RefreshAncestors()
        {
            _ancestorList.Items.Clear();
            _ancestorContext.Text = _selectedMethod != null ? _selectedMethod.DisplaySignature : string.Empty;

            if (_selectedMethod == null)
            {
                return;
            }

            IReadOnlyList<AncestorEntry> ancestors = _controller.GetAncestors(_selectedMethod);
            foreach (AncestorEntry entry in ancestors)
            {
                string secondary = entry.IsPureVirtual ? "(pure virtual)" : Location(entry.FilePath, entry.Line);
                _ancestorList.Items.Add(MakeRow("↑ " + entry.ClassName, secondary, entry, entry.IsPureVirtual));
            }

            if (ancestors.Count == 0)
            {
                _ancestorList.Items.Add(MakeRow("(declared here — no base implementation found)", null, null, true));
            }
        }

        private void RefreshDerived()
        {
            _derivedTree.Items.Clear();
            _derivedContext.Text = _selectedMethod != null ? _selectedMethod.DisplaySignature : string.Empty;

            if (_selectedMethod == null)
            {
                return;
            }

            IReadOnlyList<OverrideTreeNode> roots = _controller.GetDerivedOverrides(_selectedMethod);
            foreach (OverrideTreeNode node in roots)
            {
                _derivedTree.Items.Add(MakeTreeItem(node));
            }

            if (roots.Count == 0)
            {
                _derivedTree.Items.Add(new TreeViewItem { Header = "(no derived overrides found)", IsEnabled = false });
            }
        }

        private void ClearFunctions()
        {
            if (_functionList != null)
            {
                _functionList.Items.Clear();
            }

            if (_functionContext != null)
            {
                _functionContext.Text = string.Empty;
            }
        }

        private void ClearAncestorsAndDerived()
        {
            if (_ancestorList != null)
            {
                _ancestorList.Items.Clear();
            }

            if (_derivedTree != null)
            {
                _derivedTree.Items.Clear();
            }

            if (_ancestorContext != null)
            {
                _ancestorContext.Text = string.Empty;
            }

            if (_derivedContext != null)
            {
                _derivedContext.Text = string.Empty;
            }
        }

        // -- navigation --------------------------------------------------------------------------

        private void NavigateFromList(ListBox list)
        {
            ThreadHelper.ThrowIfNotOnUIThread();
            object tag = SelectedTag(list);

            var cls = tag as CodeClass;
            if (cls != null)
            {
                DocumentNavigator.OpenFileAtLine(cls.FilePath, cls.Line, _solutionDirectory);
                return;
            }

            var method = tag as CodeMethod;
            if (method != null)
            {
                DocumentNavigator.OpenFileAtLine(method.FilePath, method.Line, _solutionDirectory);
                return;
            }

            var ancestor = tag as AncestorEntry;
            if (ancestor != null && ancestor.CanNavigate)
            {
                DocumentNavigator.OpenFileAtLine(ancestor.FilePath, ancestor.Line, _solutionDirectory);
            }
        }

        private void DerivedTree_MouseDoubleClick(object sender, System.Windows.Input.MouseButtonEventArgs e)
        {
            ThreadHelper.ThrowIfNotOnUIThread();
            var item = _derivedTree.SelectedItem as TreeViewItem;
            if (item == null)
            {
                return;
            }

            var node = item.Tag as OverrideTreeNode;
            if (node != null && node.CanNavigate)
            {
                DocumentNavigator.OpenFileAtLine(node.FilePath, node.Line, _solutionDirectory);
            }
        }

        // -- helpers -----------------------------------------------------------------------------

        private string GetSolutionDirectory()
        {
            ThreadHelper.ThrowIfNotOnUIThread();
            try
            {
                IServiceProvider provider = ServiceProvider.GlobalProvider;
                var solution = provider.GetService(typeof(SVsSolution)) as IVsSolution;
                if (solution != null)
                {
                    string dir, file, opts;
                    if (solution.GetSolutionInfo(out dir, out file, out opts) == VSConstants.S_OK
                        && !string.IsNullOrEmpty(dir))
                    {
                        return dir;
                    }
                }
            }
            catch
            {
                // no solution / not available
            }

            return null;
        }

        private void SetStatus(string text)
        {
            if (_statusText != null)
            {
                _statusText.Text = text ?? string.Empty;
            }
        }

        private static object SelectedTag(ListBox list)
        {
            var item = list.SelectedItem as ListBoxItem;
            return item != null ? item.Tag : null;
        }

        private TreeViewItem MakeTreeItem(OverrideTreeNode node)
        {
            var item = new TreeViewItem
            {
                Header = BuildRowContent(node.ClassName, Location(node.FilePath, node.Line), false),
                Tag = node,
                IsExpanded = true,
            };

            foreach (OverrideTreeNode child in node.Children)
            {
                item.Items.Add(MakeTreeItem(child));
            }

            return item;
        }

        private ListBoxItem MakeRow(string main, string secondary, object tag, bool italic)
        {
            return new ListBoxItem { Content = BuildRowContent(main, secondary, italic), Tag = tag };
        }

        private UIElement BuildRowContent(string main, string secondary, bool italic)
        {
            var dock = new DockPanel { LastChildFill = true };

            if (!string.IsNullOrEmpty(secondary))
            {
                var right = new TextBlock
                {
                    Text = secondary,
                    Opacity = 0.6,
                    Margin = new Thickness(8, 0, 0, 0),
                    VerticalAlignment = VerticalAlignment.Center,
                };
                DockPanel.SetDock(right, Dock.Right);
                dock.Children.Add(right);
            }

            var left = new TextBlock
            {
                Text = main,
                TextTrimming = TextTrimming.CharacterEllipsis,
                VerticalAlignment = VerticalAlignment.Center,
            };
            if (italic)
            {
                left.FontStyle = FontStyles.Italic;
                left.Opacity = 0.8;
            }

            dock.Children.Add(left);
            return dock;
        }

        private TextBox MakeSearchBox(string hint)
        {
            var box = new TextBox { Margin = new Thickness(6, 2, 6, 2), ToolTip = hint };
            ApplyThemed(box);
            return box;
        }

        private ListBox MakeListBox()
        {
            var list = new ListBox { BorderThickness = new Thickness(0) };
            ApplyThemed(list);
            ScrollViewer.SetHorizontalScrollBarVisibility(list, ScrollBarVisibility.Disabled);
            return list;
        }

        private UIElement StackVertical(UIElement top, UIElement fill)
        {
            var dock = new DockPanel { LastChildFill = true };
            DockPanel.SetDock(top, Dock.Top);
            dock.Children.Add(top);
            dock.Children.Add(fill);
            return dock;
        }

        private UIElement SectionHeader(string title, out TextBlock context)
        {
            var dock = new DockPanel { LastChildFill = true, Margin = new Thickness(6, 4, 6, 2) };

            var titleBlock = new TextBlock { Text = title, FontWeight = FontWeights.Bold };
            DockPanel.SetDock(titleBlock, Dock.Left);
            dock.Children.Add(titleBlock);

            context = new TextBlock
            {
                Opacity = 0.6,
                Margin = new Thickness(8, 0, 0, 0),
                TextTrimming = TextTrimming.CharacterEllipsis,
            };
            dock.Children.Add(context);
            return dock;
        }

        private UIElement Section(UIElement header, UIElement content)
        {
            var dock = new DockPanel { LastChildFill = true };
            DockPanel.SetDock(header, Dock.Top);
            dock.Children.Add(header);
            dock.Children.Add(content);
            return dock;
        }

        private void ApplyThemed(Control control)
        {
            control.SetResourceReference(BackgroundProperty, VsBrushes.ToolWindowBackgroundKey);
            control.SetResourceReference(ForegroundProperty, VsBrushes.ToolWindowTextKey);
        }

        private static void AddRow(Grid grid, int row, UIElement element)
        {
            Grid.SetRow(element, row);
            grid.Children.Add(element);
        }

        private static RowDefinition StarRow(double weight)
        {
            return new RowDefinition { Height = new GridLength(weight, GridUnitType.Star) };
        }

        private static UIElement DockTop(UIElement element)
        {
            DockPanel.SetDock(element, Dock.Top);
            return element;
        }

        private static string Location(string filePath, int line)
        {
            if (string.IsNullOrEmpty(filePath))
            {
                return null;
            }

            string name;
            try
            {
                name = Path.GetFileName(filePath);
            }
            catch
            {
                name = filePath;
            }

            return line > 0 ? string.Format("{0} : {1}", name, line) : name;
        }

        private static string FolderKey(CodeClass c)
        {
            if (c == null || string.IsNullOrEmpty(c.FilePath))
            {
                return "(unknown)";
            }

            try
            {
                string dir = Path.GetDirectoryName(c.FilePath);
                return string.IsNullOrEmpty(dir) ? "(unknown)" : dir;
            }
            catch
            {
                return "(unknown)";
            }
        }

        private static string ShortenFolder(string folder)
        {
            if (string.IsNullOrEmpty(folder) || folder == "(unknown)")
            {
                return folder;
            }

            string[] parts = folder.Split('/', '\\');
            if (parts.Length <= 2)
            {
                return folder;
            }

            return "…" + Path.DirectorySeparatorChar + parts[parts.Length - 2] + Path.DirectorySeparatorChar + parts[parts.Length - 1];
        }
    }
}
