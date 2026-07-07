type WorkspacePageProps = {
  children: React.ReactNode;
};

export function WorkspacePage({ children }: WorkspacePageProps) {
  return <div className="space-y-6 p-8">{children}</div>;
}
