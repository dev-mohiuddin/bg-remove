"use client";

import { useState, useCallback } from "react";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import UploadZone from "@/components/UploadZone";
import ProcessingState from "@/components/ProcessingState";
import BeforeAfterSlider from "@/components/BeforeAfterSlider";
import DownloadButton from "@/components/DownloadButton";
import { removeBackground } from "@/lib/api";

export default function HomePage() {
  const [state, setState] = useState("idle");
  const [originalUrl, setOriginalUrl] = useState(null);
  const [processedUrl, setProcessedUrl] = useState(null);
  const [processedBlob, setProcessedBlob] = useState(null);
  const [fileName, setFileName] = useState("");
  const [error, setError] = useState("");

  const handleFileSelect = useCallback(async (file) => {
    setError("");
    setProcessedUrl(null);
    setProcessedBlob(null);
    const preview = URL.createObjectURL(file);
    setOriginalUrl(preview);
    setFileName(file.name);
    setState("processing");

    try {
      const { blobUrl, blob } = await removeBackground(file);
      setProcessedUrl(blobUrl);
      setProcessedBlob(blob);
      setState("done");
    } catch (err) {
      setError(err.message || "Something went wrong. Please try again.");
      setState("error");
    }
  }, []);

  const handleReset = useCallback(() => {
    if (originalUrl) URL.revokeObjectURL(originalUrl);
    if (processedUrl) URL.revokeObjectURL(processedUrl);
    setState("idle");
    setOriginalUrl(null);
    setProcessedUrl(null);
    setProcessedBlob(null);
    setFileName("");
    setError("");
  }, [originalUrl, processedUrl]);

  return (
    <>
      <div className="ambient-bg" aria-hidden="true" />
      <Header />

      <main className="flex-1 flex flex-col items-center justify-center px-6">

        
        {(state === "idle" || state === "error") && (
          <div className="w-full max-w-2xl mx-auto flex flex-col items-center py-20 fade-in">

            
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[var(--color-accent)]/8 border border-[var(--color-accent)]/15 mb-8">
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-accent)]" />
              <span className="text-xs font-medium text-[var(--color-accent-hover)] tracking-wide">
                Powered by BiRefNet AI
              </span>
            </div>

            
            <h1 className="text-5xl sm:text-6xl font-bold tracking-tight text-center text-[var(--color-text-primary)] mb-5 leading-[1.08]">
              Remove Any
              <br />
              <span className="bg-gradient-to-r from-[var(--color-accent)] via-[#818cf8] to-[#a78bfa] bg-clip-text text-transparent">
                Background
              </span>
            </h1>

            <p className="text-base sm:text-lg text-[var(--color-text-secondary)] max-w-sm text-center leading-relaxed mb-12">
              Pixel-perfect AI cutouts that preserve hair,
              fabric, and the finest edges.
            </p>

            
            <UploadZone onFileSelect={handleFileSelect} />

            
            {state === "error" && (
              <div className="w-full max-w-xl mt-4 fade-in">
                <div className="px-4 py-3 rounded-xl bg-red-500/8 border border-red-500/15">
                  <p className="text-sm text-red-400 text-center">{error}</p>
                </div>
              </div>
            )}

            
            <div className="flex flex-wrap justify-center gap-3 mt-10 fade-in-delay">
              {[
                { icon: "⚡", label: "Fast Processing" },
                { icon: "✦", label: "Pixel-Perfect" },
                { icon: "↕", label: "Full Resolution" },
              ].map((item) => (
                <div key={item.label} className="feature-badge">
                  <span>{item.icon}</span>
                  {item.label}
                </div>
              ))}
            </div>
          </div>
        )}

        
        {state === "processing" && <ProcessingState fileName={fileName} />}

        
        {state === "done" && (
          <div className="w-full flex flex-col items-center gap-10 py-10 fade-in">

            
            <BeforeAfterSlider
              originalUrl={originalUrl}
              processedUrl={processedUrl}
            />

            
            <div className="result-actions">

              
              <div className="w-full flex items-center justify-between mb-5 pb-5"
                style={{ borderBottom: "1px solid var(--color-border-subtle)" }}>
                <div className="flex items-center gap-2.5">
                  <div style={{
                    width: 34, height: 34, borderRadius: 9,
                    background: "rgba(99,102,241,0.1)",
                    border: "1px solid rgba(99,102,241,0.15)",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    flexShrink: 0,
                  }}>
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none"
                      stroke="var(--color-accent)" strokeWidth="2" strokeLinecap="round">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                      <polyline points="14 2 14 8 20 8"/>
                    </svg>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-[var(--color-text-primary)] truncate max-w-[180px]">
                      {fileName || "image.png"}
                    </p>
                    <p className="text-[11px] text-[var(--color-text-tertiary)] mt-0.5">
                      Transparent PNG · Full resolution
                    </p>
                  </div>
                </div>
                <span style={{
                  padding: "3px 9px", borderRadius: 100,
                  fontSize: 11, fontWeight: 600,
                  background: "rgba(52,211,153,0.1)",
                  border: "1px solid rgba(52,211,153,0.2)",
                  color: "#34d399",
                }}>
                  Ready
                </span>
              </div>

              <DownloadButton blob={processedBlob} fileName={fileName} />

              <div className="result-divider">
                <span>or</span>
              </div>

              <button
                onClick={handleReset}
                className="new-image-btn"
                id="new-image-button"
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none"
                  stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                  <polyline points="17 8 12 3 7 8"/>
                  <line x1="12" y1="3" x2="12" y2="15"/>
                </svg>
                Remove Another Background
              </button>

            </div>


          </div>
        )}
      </main>

      <Footer />
    </>
  );
}
