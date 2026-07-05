"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import type { UsuarioDraft } from "@/types/usuario";
import { NovoUsuarioModal } from "./NovoUsuarioModal";

type NovoUsuarioButtonProps = {
  onUpsert: (draft: UsuarioDraft) => void;
};

export function NovoUsuarioButton({ onUpsert }: NovoUsuarioButtonProps) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <Button onClick={() => setOpen(true)}>Novo Usuário</Button>

      <NovoUsuarioModal
        open={open}
        onClose={() => setOpen(false)}
        onUpsert={onUpsert}
      />
    </>
  );
}
