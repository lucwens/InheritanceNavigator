using System;
using System.ComponentModel.Design;
using Microsoft.VisualStudio.Shell;
using VSIXProject.UI;
using Task = System.Threading.Tasks.Task;

namespace VSIXProject.Commands
{
    /// <summary>
    /// Menu command (View &#8594; Other Windows &#8594; Inheritance Navigator) that shows the tool window.
    /// </summary>
    internal sealed class ShowToolWindowCommand
    {
        /// <summary>Command id, must match the &lt;Button&gt; in VSIXProjectPackage.vsct.</summary>
        public const int CommandId = 0x0100;

        /// <summary>Command set GUID, must match guidVSIXProjectPackageCmdSet in the .vsct.</summary>
        public static readonly Guid CommandSet = new Guid("b1f7c3a2-9d54-4f8e-bc31-7a2e6d5f0c11");

        private readonly AsyncPackage _package;

        private ShowToolWindowCommand(AsyncPackage package, OleMenuCommandService commandService)
        {
            _package = package ?? throw new ArgumentNullException(nameof(package));
            if (commandService == null)
            {
                throw new ArgumentNullException(nameof(commandService));
            }

            var menuCommandId = new CommandID(CommandSet, CommandId);
            var menuItem = new MenuCommand(Execute, menuCommandId);
            commandService.AddCommand(menuItem);
        }

        public static ShowToolWindowCommand Instance { get; private set; }

        public static async Task InitializeAsync(AsyncPackage package)
        {
            await package.JoinableTaskFactory.SwitchToMainThreadAsync(package.DisposalToken);

            var commandService = await package.GetServiceAsync(typeof(IMenuCommandService)) as OleMenuCommandService;
            Instance = new ShowToolWindowCommand(package, commandService);
        }

        private void Execute(object sender, EventArgs e)
        {
            _ = _package.JoinableTaskFactory.RunAsync(async () =>
            {
                ToolWindowPane window = await _package.ShowToolWindowAsync(
                    typeof(InheritanceNavigatorWindow),
                    0,
                    create: true,
                    cancellationToken: _package.DisposalToken);

                if (window == null || window.Frame == null)
                {
                    throw new NotSupportedException("Cannot create the Inheritance Navigator window.");
                }
            });
        }
    }
}
