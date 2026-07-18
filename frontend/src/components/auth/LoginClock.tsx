"use client";

import { useEffect, useState } from "react";

type LoginClockDisplay = {
  date: string;
  dateTime: string;
  time: string;
};

const dateFormatter = new Intl.DateTimeFormat("pt-BR", {
  weekday: "long",
  day: "2-digit",
  month: "long",
  year: "numeric",
});

const timeFormatter = new Intl.DateTimeFormat("pt-BR", {
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hour12: false,
});

export function formatLoginClock(now: Date): LoginClockDisplay {
  return {
    date: dateFormatter.format(now),
    dateTime: now.toISOString(),
    time: timeFormatter.format(now),
  };
}

export function LoginClock() {
  const [display, setDisplay] = useState<LoginClockDisplay | null>(null);
  const completeTime = display?.time ?? "--:--:--";
  const visibleTime = completeTime.slice(0, 5);
  const dateWithoutYear = display?.date.replace(/ de \d{4}$/, "") ?? "\u00a0";
  const visibleDate = display
    ? dateWithoutYear.charAt(0).toLocaleUpperCase("pt-BR") +
      dateWithoutYear.slice(1)
    : dateWithoutYear;

  useEffect(() => {
    function updateClock() {
      setDisplay(formatLoginClock(new Date()));
    }

    updateClock();
    const intervalId = window.setInterval(updateClock, 60_000);

    return () => window.clearInterval(intervalId);
  }, []);

  return (
    <div
      className="min-w-0 text-center"
      aria-label="Data e hora atuais"
      aria-live="off"
    >
      <time
        className="block whitespace-nowrap text-[52px] font-thin leading-none tabular-nums tracking-[-0.05em] text-zinc-800 sm:text-[62px] 2xl:text-[68px] [@media(max-height:700px)]:text-[48px]"
        dateTime={display?.dateTime}
      >
        {visibleTime}
      </time>
      <p className="mt-1 min-h-4 whitespace-nowrap text-[13px] font-light leading-tight tracking-wide text-zinc-400 sm:text-sm">
        {visibleDate}
      </p>
    </div>
  );
}
