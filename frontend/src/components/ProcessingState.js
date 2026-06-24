"use client";

import { useEffect, useRef } from "react";
import { loadSocialBar } from "@/lib/adsterra";

const DEFAULT_LABELS = {
  loading: "Loading image",
  segmenting: "AI segmentation",
  matting: "Alpha matting",
  refining: "Edge refinement",
  compositing: "Compositing",
  encoding: "Encoding",
  done: "Complete",
  queued: "Queued",
};

export default function ProcessingState({ fileName, progress, stageLabels }) {
  const adCleanup = useRef(null);
  const labels = stageLabels || DEFAULT_LABELS;

  useEffect(() => {
    const { cleanup } = loadSocialBar();
    adCleanup.current = cleanup;
    return () => {
      if (adCleanup.current) adCleanup.current();
    };
  }, []);

  const pct = Math.round((progress?.progress || 0) * 100);
  const stageLabel = labels[progress?.stage] || progress?.stage || "Processing";
  const isWorking = progress?.status !== "done" && progress?.status !== "error";

  return (
    <div className="flex flex-col items-center justify-center py-20 fade-in">
      {/* Spinner rings */}
      <div className="relative flex items-center justify-center mb-8">
        <div className="processing-ring-outer" />
        <div className="processing-ring" />
        <div className="absolute w-3 h-3 rounded-full bg-[var(--color-accent)] processing-pulse" />
      </div>

      {/* Stage label + percentage */}
      <div className="text-center mb-2">
        <p className="text-base font-medium text-[var(--color-text-primary)] mb-1.5">
          {stageLabel}…
        </p>
        <p className="text-sm text-[var(--color-text-tertiary)] max-w-xs">
          Our AI is analyzing edges, hair, and transparency in{" "}
          <span className="text-[var(--color-text-secondary)]">{fileName}</span>
        </p>
      </div>

      {/* Real progress bar */}
      <div className="mt-6 w-64 h-1.5 rounded-full bg-[var(--color-border-subtle)] overflow-hidden">
        <div
          className="h-full rounded-full bg-gradient-to-r from-[var(--color-accent)] to-[#8b5cf6] transition-all duration-300 ease-out"
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="mt-2 text-xs text-[var(--color-text-tertiary)] tabular-nums">{pct}%</p>

      {/* Stage steps indicator */}
      <div className="mt-8 flex flex-col gap-2 w-64">
        {["loading", "segmenting", "matting", "refining", "compositing", "encoding"].map((s) => {
          const stagePct = stageToPct(s);
          const done = (progress?.progress || 0) >= stagePct;
          const active = progress?.stage === s && isWorking;
          return (
            <div key={s} className="flex items-center gap-3">
              <div
                className="w-4 h-4 rounded-full flex items-center justify-center flex-shrink-0 transition-colors"
                style={{
                  background: done
                    ? "rgba(52,211,153,0.15)"
                    : active
                    ? "rgba(99,102,241,0.15)"
                    : "rgba(255,255,255,0.03)",
                  border: done
                    ? "1px solid rgba(52,211,153,0.3)"
                    : active
                    ? "1px solid rgba(99,102,241,0.3)"
                    : "1px solid var(--color-border-subtle)",
                }}
              >
                {done && (
                  <svg width="9" height="9" viewBox="0 0 24 24" fill="none"
                    stroke="#34d399" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                )}
                {active && (
                  <div className="w-1.5 h-1.5 rounded-full bg-[var(--color-accent)] processing-pulse" />
                )}
              </div>
              <span
                className="text-xs transition-colors"
                style={{
                  color: done
                    ? "var(--color-text-secondary)"
                    : active
                    ? "var(--color-text-primary)"
                    : "var(--color-text-tertiary)",
                  fontWeight: active ? 600 : 400,
                }}
              >
                {labels[s] || s}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function stageToPct(stage) {
  const map = {
    loading: 0.02,
    segmenting: 0.10,
    matting: 0.65,
    refining: 0.85,
    compositing: 0.92,
    encoding: 0.96,
    done: 1.0,
  };
  return map[stage] ?? 0;
}
