"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import type { ClienteDraft } from "@/types/cliente";
import { NovoClienteModal } from "./NovoClienteModal";

type NovoClienteButtonProps = {
  onCreate: (draft: ClienteDraft) => void;
};

export function NovoClienteButton({ onCreate }: NovoClienteButtonProps) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <Button onClick={() => setOpen(true)}>Novo Cliente</Button>

      <NovoClienteModal
        open={open}
        onClose={() => setOpen(false)}
        onCreate={onCreate}
      />
    </>
  );
}
