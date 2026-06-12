using System.Runtime.InteropServices;
using Microsoft.VisualStudio.Shell;

namespace VSIXProject.UI
{
    /// <summary>
    /// Dockable tool window that hosts the <see cref="InheritanceNavigatorControl"/>. Behaves like the
    /// Solution Explorer (floatable, dockable, pinnable).
    /// </summary>
    [Guid(WindowGuidString)]
    public sealed class InheritanceNavigatorWindow : ToolWindowPane
    {
        public const string WindowGuidString = "c2e8d4b3-0a65-4019-9d42-8b3f7e6a1d22";

        public InheritanceNavigatorWindow() : base(null)
        {
            Caption = "Inheritance Navigator";
            Content = new InheritanceNavigatorControl();
        }
    }
}
