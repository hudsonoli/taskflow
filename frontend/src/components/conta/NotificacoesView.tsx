"use client";

import { useState } from "react";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { Switch } from "@/components/ui/Switch";

type ChannelKey = "Sistema" | "Email" | "WhatsApp" | "Push";

const initialChannels: Record<ChannelKey, boolean> = {
  Sistema: true,
  Email: true,
  WhatsApp: false,
  Push: false,
};

export function NotificacoesView() {
  const [channels, setChannels] = useState(initialChannels);

  return (
    <div className="p-8">
      <PageHeader
        title="Notificações"
        description="Preferências de alertas e canais de comunicação."
      />

      <Card>
        <div className="space-y-3">
          {Object.keys(channels).map((key) => {
            const channel = key as ChannelKey;

            return (
              <div
                key={channel}
                className="flex items-center justify-between rounded-2xl border border-zinc-200 px-4 py-4"
              >
                <div>
                  <p className="font-medium text-zinc-900">{channel}</p>
                  <p className="mt-1 text-sm text-zinc-500">
                    {channels[channel] ? "Ativada" : "Desativada"}
                  </p>
                </div>

                <Switch
                  checked={channels[channel]}
                  label={channel}
                  onCheckedChange={(checked) =>
                    setChannels((current) => ({
                      ...current,
                      [channel]: checked,
                    }))
                  }
                />
              </div>
            );
          })}
        </div>
      </Card>
    </div>
  );
}
