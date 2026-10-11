import { useEffect, useMemo, useState } from "react";

const RESEND_COOLDOWN_SECONDS = 60;

export function useResendCooldown() {
  const [secondsLeft, setSecondsLeft] = useState(0);

  useEffect(() => {
    if (secondsLeft <= 0) {
      return;
    }

    const timerId = window.setInterval(() => {
      setSecondsLeft((current) => (current > 0 ? current - 1 : 0));
    }, 1000);

    return () => window.clearInterval(timerId);
  }, [secondsLeft]);

  const canResend = secondsLeft <= 0;

  const start = () => {
    setSecondsLeft(RESEND_COOLDOWN_SECONDS);
  };

  return useMemo(
    () => ({ secondsLeft, canResend, start }),
    [secondsLeft, canResend],
  );
}
