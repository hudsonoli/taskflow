import type { Metadata } from "next";
import { Roboto } from "next/font/google";
import { LoginClock } from "@/components/auth/LoginClock";
import { LoginForm } from "@/components/auth/LoginForm";

const loginRoboto = Roboto({
  subsets: ["latin"],
  weight: ["100", "300", "400", "600"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Entrar | TaskFloww",
};

type LoginPageProps = {
  searchParams: Promise<{
    returnTo?: string | string[];
  }>;
};

export default async function LoginPage({ searchParams }: LoginPageProps) {
  const params = await searchParams;
  const returnTo = typeof params.returnTo === "string" ? params.returnTo : null;

  return (
    <main
      className={`${loginRoboto.className} fixed inset-0 z-[100] isolate h-dvh overflow-hidden bg-white`}
    >
      <style>{`
        @keyframes box-aurora-drift {
          0%, 100% { transform: translate3d(-2%, 1%, 0) scale(1); }
          50% { transform: translate3d(4%, -3%, 0) scale(1.07); }
        }
        @keyframes box-wave-drift {
          0%, 100% { transform: translate3d(0, 0, 0) rotate(-7deg) scale(1); }
          50% { transform: translate3d(-2.5%, 2%, 0) rotate(-4deg) scale(1.035); }
        }
        @keyframes box-particle-drift {
          0%, 100% { transform: translate3d(0, 0, 0) scale(0.9); opacity: 0.42; }
          50% { transform: translate3d(8px, -10px, 0) scale(1.1); opacity: 0.8; }
        }
        [data-login-card] label > span {
          color: #3c3c3c;
          font-family: inherit;
          font-size: 13px;
          font-weight: 600;
        }
        @media (min-width: 640px) {
          [data-login-card] label > span { font-size: 14px; }
        }
        @media (prefers-reduced-motion: reduce) {
          [data-login-aurora],
          [data-login-wave],
          [data-login-particle] { animation: none !important; }
        }
      `}</style>

      <div
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_14%,#ffffff_0%,rgba(250,250,250,0.94)_44%,rgba(245,245,245,0.88)_100%)]"
        aria-hidden="true"
      />
      <div
        data-login-aurora
        className="pointer-events-none absolute -bottom-[14%] -left-[10%] h-[64%] w-[68%] will-change-transform rounded-[50%] bg-[radial-gradient(ellipse_at_center,rgba(245,130,32,0.18)_0%,rgba(245,130,32,0.10)_40%,transparent_72%)] blur-[46px] [animation:box-aurora-drift_52s_ease-in-out_infinite]"
        aria-hidden="true"
      />
      <div
        data-login-aurora
        className="pointer-events-none absolute bottom-[4%] left-[24%] h-[34%] w-[34%] will-change-transform rounded-full bg-[radial-gradient(circle,rgba(245,130,32,0.10)_0%,transparent_70%)] blur-[38px] [animation:box-aurora-drift_56s_ease-in-out_infinite_reverse]"
        aria-hidden="true"
      />
      <div
        data-login-aurora
        className="pointer-events-none absolute -right-[10%] -top-[8%] h-[64%] w-[64%] will-change-transform rounded-[48%] bg-[radial-gradient(ellipse_at_center,rgba(120,125,135,0.10)_0%,rgba(237,237,237,0.46)_42%,transparent_72%)] blur-[44px] [animation:box-aurora-drift_58s_ease-in-out_infinite_reverse]"
        aria-hidden="true"
      />

      <div
        data-login-wave
        className="pointer-events-none absolute -left-[10%] top-[27%] h-[34%] w-[120%] will-change-transform rounded-[50%] border border-white/85 shadow-[0_0_28px_rgba(255,255,255,0.72)] [animation:box-wave-drift_54s_ease-in-out_infinite]"
        aria-hidden="true"
      />
      <div
        data-login-wave
        className="pointer-events-none absolute -left-[6%] top-[34%] h-[30%] w-[112%] will-change-transform rounded-[50%] border border-white/65 shadow-[0_0_22px_rgba(255,255,255,0.58)] [animation:box-wave-drift_58s_ease-in-out_infinite_reverse]"
        aria-hidden="true"
      />
      <div
        data-login-wave
        className="pointer-events-none absolute -left-[14%] top-[42%] h-[25%] w-[128%] will-change-transform rounded-[50%] border border-white/55 [animation:box-wave-drift_60s_ease-in-out_infinite]"
        aria-hidden="true"
      />

      <div className="pointer-events-none absolute inset-0" aria-hidden="true">
        <span data-login-particle className="absolute left-[12%] top-[24%] h-1.5 w-1.5 rounded-full bg-white shadow-[0_0_14px_rgba(255,255,255,0.95)] [animation:box-particle-drift_52s_ease-in-out_infinite]" />
        <span data-login-particle className="absolute left-[29%] top-[68%] h-1 w-1 rounded-full bg-white shadow-[0_0_12px_rgba(255,255,255,0.9)] [animation:box-particle-drift_58s_ease-in-out_infinite_reverse]" />
        <span data-login-particle className="absolute right-[18%] top-[20%] h-1.5 w-1.5 rounded-full bg-white shadow-[0_0_14px_rgba(255,255,255,0.95)] [animation:box-particle-drift_56s_ease-in-out_infinite]" />
        <span data-login-particle className="absolute right-[11%] top-[61%] h-1 w-1 rounded-full bg-white shadow-[0_0_12px_rgba(255,255,255,0.88)] [animation:box-particle-drift_60s_ease-in-out_infinite_reverse]" />
        <span data-login-particle className="absolute left-[48%] top-[16%] h-1 w-1 rounded-full bg-white shadow-[0_0_10px_rgba(255,255,255,0.85)] [animation:box-particle-drift_54s_ease-in-out_infinite]" />
      </div>

      <div className="relative z-10 h-full overflow-x-hidden overflow-y-auto">
        <div className="flex min-h-full w-full p-4 sm:p-6 [@media(max-height:640px)]:p-3">
          <div className="mx-auto my-auto flex w-full max-w-[410px] flex-col items-center">
            <LoginClock />

            <section
              data-login-card
              className="mt-[18px] w-full rounded-[28px] border border-white/75 bg-white/60 p-5 shadow-[0_12px_32px_rgba(0,0,0,0.06)] backdrop-blur-[20px] sm:mt-5 sm:p-7 [@media(max-height:700px)]:mt-4 [@media(max-height:700px)]:p-5"
              aria-label="Acesso ao TaskFloww"
            >
              <LoginForm returnTo={returnTo} />

              <p className="mt-4 whitespace-nowrap text-center text-[13px] font-normal text-zinc-500 max-[360px]:text-xs">
                taskflow - Uso interno BOX
              </p>
            </section>
          </div>
        </div>
      </div>
    </main>
  );
}
