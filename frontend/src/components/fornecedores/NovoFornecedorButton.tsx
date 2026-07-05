import { Button } from "@/components/ui/Button";

type NovoFornecedorButtonProps = {
  onClick: () => void;
  disabled?: boolean;
};

export function NovoFornecedorButton({
  onClick,
  disabled = false,
}: NovoFornecedorButtonProps) {
  return (
    <Button onClick={onClick} disabled={disabled}>
      Novo Fornecedor
    </Button>
  );
}
