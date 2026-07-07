import { EmptyState } from "@/components/ui/EmptyState";

type WorkspaceEmptyStateProps = {
  title: string;
  description: string;
};

export function WorkspaceEmptyState({
  title,
  description,
}: WorkspaceEmptyStateProps) {
  return <EmptyState title={title} description={description} />;
}
