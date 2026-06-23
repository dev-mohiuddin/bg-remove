"use client";

import { useState, useCallback } from "react";
import { triggerDirectLink } from "@/lib/adsterra";


export default function DownloadButton({ blob, fileName }) {
  const [saving, setSaving] = useState(false);

  const handleDownload = useCallback(() => {
    if (saving) return;
    setSaving(true);


    triggerDirectLink();


    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `bg-removed-${fileName || "image"}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    setTimeout(() => {
      URL.revokeObjectURL(url);
      setSaving(false);
    }, 1800);
  }, [blob, fileName, saving]);

  return (
    <button
      onClick={handleDownload}
      disabled={saving}
      className="btn-download btn-download-full"
      id="download-button"
    >
      {saving ? (
        <>
          
          <svg
            width="18" height="18" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"
            strokeLinejoin="round"
            style={{ animation: "spin 0.8s linear infinite" }}
          >
            <path d="M21 12a9 9 0 1 1-6.219-8.56" />
          </svg>
          Saving…
        </>
      ) : (
        <>
          
          <svg
            width="18" height="18" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="7 10 12 15 17 10" />
            <line x1="12" y1="15" x2="12" y2="3" />
          </svg>
          Download HD PNG
          
          <span style={{
            marginLeft: 6,
            padding: "2px 8px",
            borderRadius: 100,
            fontSize: 11,
            fontWeight: 600,
            letterSpacing: "0.04em",
            background: "rgba(255,255,255,0.15)",
            color: "rgba(255,255,255,0.85)",
            textTransform: "uppercase",
          }}>
            Free
          </span>
        </>
      )}
    </button>
  );
}
