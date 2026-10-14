"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ApiClientError, approveOkBrief } from "../../app/lib/api";

const MAIL_LABELS: Record<string, string> = {
  "ikke sat op": "Mail er ikke sat op – send PDF'en selv.",
  fejlede: "Mailen kunne ikke sendes – send PDF'en selv.",
};

/** Konsulentens kontrol: direktøren ser først Til OK, når den er godkendt. */
export function ApproveBriefButton() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function approve() {
    setBusy(true);
    setMessage(null);
    try {
      const result = await approveOkBrief();
      setMessage(
        `Godkendt. ${MAIL_LABELS[result.mail] ?? `Mail ${result.mail}.`}`,
      );
      router.refresh();
    } catch (err) {
      setMessage(
        err instanceof ApiClientError
          ? err.message
          : "Kunne ikke godkende. Prøv igen.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <span className="approve">
      <button
        type="button"
        className="btn-primary"
        onClick={approve}
        disabled={busy}
      >
        {busy ? "Godkender…" : "Godkend og send"}
      </button>
      {message ? (
        <span className="small" role="status">
          {message}
        </span>
      ) : null}
    </span>
  );
}
