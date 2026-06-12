using System;
using System.IO;
using Microsoft.VisualStudio.Shell;
using Microsoft.VisualStudio.Shell.Interop;
using Microsoft.VisualStudio.TextManager.Interop;
using IServiceProvider = System.IServiceProvider;

namespace VSIXProject.UI
{
    /// <summary>
    /// Opens a source file in the Visual Studio editor and scrolls to a 1-based line, using only VS
    /// shell services (no EnvDTE). Powers double-click navigation in the tool window.
    /// </summary>
    internal static class DocumentNavigator
    {
        public static void OpenFileAtLine(string filePath, int oneBasedLine, string baseDirectory)
        {
            ThreadHelper.ThrowIfNotOnUIThread();

            string resolved = Resolve(filePath, baseDirectory);
            if (resolved == null)
            {
                return;
            }

            try
            {
                IServiceProvider provider = ServiceProvider.GlobalProvider;
                IVsUIHierarchy hierarchy;
                uint itemId;
                IVsWindowFrame windowFrame;

                VsShellUtilities.OpenDocument(
                    provider,
                    resolved,
                    Guid.Empty,
                    out hierarchy,
                    out itemId,
                    out windowFrame);

                if (windowFrame == null)
                {
                    return;
                }

                windowFrame.Show();

                IVsTextView textView = VsShellUtilities.GetTextView(windowFrame);
                if (textView == null)
                {
                    return;
                }

                int line = oneBasedLine > 0 ? oneBasedLine - 1 : 0;
                textView.SetCaretPos(line, 0);
                textView.CenterLines(line, 1);
                textView.SetSelection(line, 0, line, 0);
            }
            catch
            {
                // Navigation is best-effort; never let a bad path crash the tool window.
            }
        }

        private static string Resolve(string filePath, string baseDirectory)
        {
            if (string.IsNullOrEmpty(filePath))
            {
                return null;
            }

            try
            {
                string candidate = filePath;
                if (!Path.IsPathRooted(candidate) && !string.IsNullOrEmpty(baseDirectory))
                {
                    candidate = Path.GetFullPath(Path.Combine(baseDirectory, candidate));
                }

                return File.Exists(candidate) ? candidate : null;
            }
            catch
            {
                return null;
            }
        }
    }
}
