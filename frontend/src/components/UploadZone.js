"use client";

import { useCallback } from "react";
import { useDropzone } from "react-dropzone";


export default function UploadZone({ onFileSelect }) {
  const onDrop = useCallback(
    (acceptedFiles) => {
      if (acceptedFiles.length > 0) {
        onFileSelect(acceptedFiles[0]);
      }
    },
    [onFileSelect]
  );

  const { getRootProps, getInputProps, isDragActive, fileRejections } =
    useDropzone({
      onDrop,
      accept: {
        "image/jpeg": [".jpg", ".jpeg"],
        "image/png": [".png"],
        "image/webp": [".webp"],
      },
      maxSize: 20 * 1024 * 1024,
      multiple: false,
    });

  const hasError = fileRejections.length > 0;

  return (
    <div className="backlight-glow w-full max-w-xl mx-auto">
      <div
        {...getRootProps()}
        className={`upload-zone cursor-pointer px-8 py-16 text-center transition-all ${
          isDragActive ? "drag-active" : ""
        }`}
        id="upload-zone"
      >
        <input {...getInputProps()} id="file-input" />

        
        <div className="flex justify-center mb-5">
          <div
            className={`w-14 h-14 rounded-2xl flex items-center justify-center transition-colors duration-300 ${
              isDragActive
                ? "bg-[var(--color-accent-glow)]"
                : "bg-[var(--color-surface-card)]"
            }`}
          >
            <svg
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              className={`transition-colors duration-300 ${
                isDragActive
                  ? "stroke-[var(--color-accent)]"
                  : "stroke-[var(--color-text-secondary)]"
              }`}
            >
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
          </div>
        </div>

        
        {isDragActive ? (
          <div className="fade-in">
            <p className="text-base font-medium text-[var(--color-accent)]">
              Drop your image here
            </p>
          </div>
        ) : (
          <>
            <p className="text-base font-medium text-[var(--color-text-primary)] mb-1.5">
              Drop an image here, or{" "}
              <span className="text-[var(--color-accent)] hover:text-[var(--color-accent-hover)] transition-colors cursor-pointer">
                browse
              </span>
            </p>
            <p className="text-sm text-[var(--color-text-tertiary)]">
              JPEG, PNG, or WebP · Up to 20 MB
            </p>
          </>
        )}

        
        {hasError && (
          <p className="mt-3 text-sm text-red-400 fade-in">
            {fileRejections[0]?.errors[0]?.message ||
              "Invalid file. Please try a different image."}
          </p>
        )}
      </div>
    </div>
  );
}
