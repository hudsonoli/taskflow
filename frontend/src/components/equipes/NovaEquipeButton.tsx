"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import type { EquipeDraft } from "@/types/equipe";
import { NovaEquipeModal } from "./NovaEquipeModal";

type NovaEquipeButtonProps = {
  onUpsert: (draft: EquipeDraft) => void;
};

export function NovaEquipeButton({ onUpsert }: NovaEquipeButtonProps) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <Button onClick={() => setOpen(true)}>Nova Equipe</Button>

      <NovaEquipeModal
        open={open}
        onClose={() => setOpen(false)}
        onUpsert={onUpsert}
      />
    </>
  );
}
