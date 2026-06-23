"use client";

import {
  ReactCompareSlider,
  ReactCompareSliderImage,
} from "react-compare-slider";


export default function BeforeAfterSlider({ originalUrl, processedUrl }) {
  return (
    <div className="w-full max-w-3xl mx-auto fade-in flex flex-col gap-4">

      
      <div className="flex items-center justify-between px-1">
        <div className="flex items-center gap-2.5">
          
          <div style={{
            width: 28, height: 28, borderRadius: "50%",
            background: "linear-gradient(135deg, #34d399, #059669)",
            display: "flex", alignItems: "center", justifyContent: "center",
            boxShadow: "0 4px 12px rgba(52, 211, 153, 0.3)",
            flexShrink: 0,
          }}>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
              stroke="white" strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="20 6 9 17 4 12" />
            </svg>
          </div>
          <div>
            <p className="text-sm font-semibold text-[var(--color-text-primary)]">
              Background Removed
            </p>
            <p className="text-xs text-[var(--color-text-tertiary)] mt-0.5">
              Drag the slider to compare
            </p>
          </div>
        </div>

        
        <div className="flex items-center gap-3">
          <span className="slider-label">
            <span className="label-dot" style={{ background: "var(--color-border-default)" }} />
            Original
          </span>
          <span className="slider-label">
            <span className="label-dot" style={{ background: "var(--color-accent)" }} />
            Removed
          </span>
        </div>
      </div>

      
      <div className="image-result-container">
        <ReactCompareSlider
          itemOne={
            <ReactCompareSliderImage
              src={originalUrl}
              alt="Original image"
              style={{ objectFit: "contain", width: "100%", height: "100%" }}
            />
          }
          itemTwo={
            <div className="checkerboard w-full h-full flex items-center justify-center">
              <ReactCompareSliderImage
                src={processedUrl}
                alt="Background removed"
                style={{ objectFit: "contain", width: "100%", height: "100%" }}
              />
            </div>
          }
          handle={<SliderHandle />}
          position={50}
          style={{
            height: "min(62vh, 520px)",
            width: "100%",
          }}
        />
      </div>
    </div>
  );
}


function SliderHandle() {
  return (
    <div className="flex flex-col items-center justify-center h-full">
      
      <div style={{
        width: 2,
        height: "100%",
        background: "linear-gradient(to bottom, transparent 0%, rgba(255,255,255,0.5) 20%, rgba(255,255,255,0.5) 80%, transparent 100%)",
      }} />

      
      <div className="slider-handle absolute" style={{
        width: 44,
        height: 44,
        borderRadius: "50%",
        background: "rgba(255,255,255,0.97)",
        border: "2px solid var(--color-accent)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        boxShadow: "0 4px 20px rgba(0,0,0,0.35), 0 0 0 5px rgba(99,102,241,0.12)",
        cursor: "ew-resize",
        gap: 2,
      }}>
        <svg width="8" height="14" viewBox="0 0 8 14" fill="none"
          stroke="var(--color-accent)" strokeWidth="2" strokeLinecap="round">
          <path d="M5 1L1 7l4 6" />
        </svg>
        <svg width="8" height="14" viewBox="0 0 8 14" fill="none"
          stroke="var(--color-accent)" strokeWidth="2" strokeLinecap="round">
          <path d="M3 1l4 6-4 6" />
        </svg>
      </div>
    </div>
  );
}
