import { useState } from "react";

interface Props {
  text: string;
  label?: string;
  /** Called after a successful copy (used by the exorcism animation trigger). */
  onCopied?: () => void;
}

export function CopyButton({ text, label = "Copy", onCopied }: Props) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      onCopied?.();
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for environments without clipboard API
      const el = document.createElement("textarea");
      el.value = text;
      el.style.position = "fixed";
      el.style.opacity = "0";
      document.body.appendChild(el);
      el.select();
      document.execCommand("copy");
      document.body.removeChild(el);
      setCopied(true);
      onCopied?.();
      setTimeout(() => setCopied(false), 2000);
    }
  }

  return (
    <button
      className={`copy-btn ${copied ? "copy-btn--copied" : ""}`}
      onClick={handleCopy}
      aria-label={copied ? "Copied!" : label}
      title={copied ? "Copied!" : label}
    >
      {copied ? "✓ Copied!" : label}
    </button>
  );
}
