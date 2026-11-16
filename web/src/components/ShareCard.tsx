import { useState } from "react";
import type { Report } from "../types/report";
import { buildShareCardData, EMPTY_CARD_TEXT, type ShareCardData } from "../utils/shareCard";

const W = 1200;
const H = 630;

const LABEL_COLOURS: Record<string, string> = {
  Peaceful: "#7fd99a",
  Restless: "#e8d27a",
  Haunted: "#f0a35e",
  Cursed: "#ff7a7a",
};

/** Draw the card. Uses only ShareCardData: no identifiers ever reach the canvas. */
function draw(ctx: CanvasRenderingContext2D, d: ShareCardData, demo: boolean) {
  const grad = ctx.createLinearGradient(0, 0, 0, H);
  grad.addColorStop(0, "#14142a");
  grad.addColorStop(1, "#0d150a");
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, W, H);

  ctx.textBaseline = "alphabetic";
  ctx.fillStyle = "#8a8ac0";
  ctx.font = "italic 34px serif";
  ctx.fillText("Graveyard Shift", 60, 90);

  if (d.empty) {
    ctx.fillStyle = "#e8e0c0";
    ctx.font = "bold 64px sans-serif";
    ctx.fillText(EMPTY_CARD_TEXT, 60, 330);
  } else {
    ctx.fillStyle = LABEL_COLOURS[d.label] ?? "#e8e0c0";
    ctx.font = "bold 150px sans-serif";
    ctx.fillText(`${d.score}/100`, 60, 280);
    ctx.font = "bold 64px sans-serif";
    ctx.fillText(d.label, 60, 360);

    ctx.fillStyle = "#e8e0c0";
    ctx.font = "40px sans-serif";
    ctx.fillText(`$${d.totalCost.toFixed(2)}/mo wasted (estimated)`, 60, 440);

    ctx.fillStyle = "#8a8ac0";
    ctx.font = "28px sans-serif";
    ctx.fillText("Costliest ghosts", 700, 190);
    ctx.fillStyle = "#e8e0c0";
    ctx.font = "bold 36px sans-serif";
    d.topNames.forEach((n, i) => {
      const text = n.length > 22 ? `${n.slice(0, 21)}…` : n;
      ctx.fillText(`${i + 1}. ${text}`, 700, 250 + i * 60);
    });
  }

  ctx.fillStyle = "#8a8ac0";
  ctx.font = "24px sans-serif";
  ctx.fillText(
    demo ? "Sample data · Heuristic score, not an AWS metric" : "Heuristic score, not an AWS metric",
    60,
    H - 50,
  );
}

function canvasSupported(): boolean {
  try {
    const c = document.createElement("canvas");
    return typeof c.toBlob === "function" && !!c.getContext("2d");
  } catch {
    return false;
  }
}

/** "Share my graveyard": renders a PNG in the browser and downloads it. Nothing is uploaded. */
export function ShareCard({ report }: { report: Report }) {
  const [supported] = useState(canvasSupported);
  const [error, setError] = useState<string | null>(null);

  function handleClick() {
    setError(null);
    const canvas = document.createElement("canvas");
    canvas.width = W;
    canvas.height = H;
    const ctx = canvas.getContext("2d");
    if (!ctx) {
      setError("Your browser can't draw the card.");
      return;
    }
    draw(ctx, buildShareCardData(report), report.demo);
    canvas.toBlob((blob) => {
      if (!blob) {
        setError("Could not create the image.");
        return;
      }
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "my-graveyard.png";
      a.click();
      URL.revokeObjectURL(url);
    }, "image/png");
  }

  return (
    <div className="share-card">
      <button type="button" className="share-btn" onClick={handleClick} disabled={!supported}>
        📸 Share my graveyard
      </button>
      <span className="share-note">
        {supported
          ? "Saves an image on your device. Nothing is uploaded."
          : "Image export isn't available in this browser."}
      </span>
      {error && (
        <span role="alert" className="share-error">
          {error}
        </span>
      )}
    </div>
  );
}
