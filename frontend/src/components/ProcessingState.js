"use client";

import { useEffect, useRef } from "react";
import { loadSocialBar } from "@/lib/adsterra";


export default function ProcessingState({ fileName }) {
  const adCleanup = useRef(null);

  useEffect(() => {

    const { cleanup } = loadSocialBar();
    adCleanup.current = cleanup;

    return () => {
      if (adCleanup.current) {
        adCleanup.current();
      }
    };
  }, []);

  return (
    <div className="flex flex-col items-center justify-center py-20 fade-in">
      
      <div className="relative flex items-center justify-center mb-8">
        
        <div className="processing-ring-outer" />
        
        <div className="processing-ring" />
        
        <div className="absolute w-3 h-3 rounded-full bg-[var(--color-accent)] processing-pulse" />
      </div>

      
      <div className="text-center">
        <p className="text-base font-medium text-[var(--color-text-primary)] mb-1.5">
          Removing background...
        </p>
        <p className="text-sm text-[var(--color-text-tertiary)] max-w-xs">
          Our AI is analyzing edges, hair, and transparency in{" "}
          <span className="text-[var(--color-text-secondary)]">{fileName}</span>
        </p>
      </div>

      
      <div className="mt-6 w-64 h-1 rounded-full bg-[var(--color-border-subtle)] overflow-hidden">
        <div
          className="h-full rounded-full bg-gradient-to-r from-[var(--color-accent)] to-[#8b5cf6]"
          style={{
            animation: "progress-fill 8s ease-in-out forwards",
          }}
        />
      </div>

      <style jsx>{`
        @keyframes progress-fill {
          0% {
            width: 0%;
          }
          20% {
            width: 25%;
          }
          50% {
            width: 55%;
          }
          80% {
            width: 80%;
          }
          100% {
            width: 95%;
          }
        }
      `}</style>
    </div>
  );
}
