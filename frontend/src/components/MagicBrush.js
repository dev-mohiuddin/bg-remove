"use client";

import { useRef, useState, useEffect, useCallback } from "react";

/**
 * MagicBrush — Manual touch-up tool for pixel-perfect alpha mask editing.
 *
 * Features:
 * - Erase mode: remove background (set alpha to 0)
 * - Restore mode: bring back foreground (set alpha to 255)
 * - Feather mode: soften edges (blur alpha locally)
 * - Adjustable brush size, hardness, and opacity
 * - Real-time canvas preview with checkerboard background
 * - Export edited mask as PNG for server compositing
 *
 * Props:
 * - imageUrl: processed image URL (RGBA PNG with transparency)
 * - maskUrl: raw alpha mask URL (grayscale PNG)
 * - originalImageUrl: original image URL (for reference)
 * - onApply: callback(editedMaskBlob) when user clicks "Apply"
 * - onCancel: callback when user clicks "Cancel"
 */
export default function MagicBrush({
  imageUrl,
  maskUrl,
  originalImageUrl,
  onApply,
  onCancel,
}) {
  const canvasRef = useRef(null);
  const maskCanvasRef = useRef(null); // Off-screen mask canvas
  const displayCanvasRef = useRef(null); // On-screen display canvas
  const containerRef = useRef(null);

  const [tool, setTool] = useState("erase"); // erase | restore | feather
  const [brushSize, setBrushSize] = useState(40);
  const [hardness, setHardness] = useState(50); // 0-100
  const [opacity, setOpacity] = useState(100); // 0-100
  const [isDrawing, setIsDrawing] = useState(false);
  const [showMask, setShowMask] = useState(false); // Toggle mask overlay
  const [canvasSize, setCanvasSize] = useState({ width: 0, height: 0 });

  const lastPosRef = useRef(null);
  const maskImageRef = useRef(null);
  const processedImageRef = useRef(null);

  // Load mask and processed image
  useEffect(() => {
    if (!maskUrl || !imageUrl) return;

    const maskImg = new Image();
    maskImg.crossOrigin = "anonymous";
    maskImg.onload = () => {
      maskImageRef.current = maskImg;

      // Initialize mask canvas
      const maskCanvas = maskCanvasRef.current;
      maskCanvas.width = maskImg.width;
      maskCanvas.height = maskImg.height;
      const maskCtx = maskCanvas.getContext("2d");
      maskCtx.drawImage(maskImg, 0, 0);

      // Set display canvas size
      const maxDisplay = 600;
      const scale = Math.min(maxDisplay / maskImg.width, maxDisplay / maskImg.height, 1);
      const displayW = Math.round(maskImg.width * scale);
      const displayH = Math.round(maskImg.height * scale);
      setCanvasSize({ width: displayW, height: displayH });

      const displayCanvas = displayCanvasRef.current;
      displayCanvas.width = maskImg.width;
      displayCanvas.height = maskImg.height;
      displayCanvas.style.width = `${displayW}px`;
      displayCanvas.style.height = `${displayH}px`;

      renderDisplay();
    };
    maskImg.src = maskUrl;

    const procImg = new Image();
    procImg.crossOrigin = "anonymous";
    procImg.onload = () => {
      processedImageRef.current = procImg;
      renderDisplay();
    };
    procImg.src = imageUrl;
  }, [maskUrl, imageUrl]);

  const renderDisplay = useCallback(() => {
    const displayCanvas = displayCanvasRef.current;
    if (!displayCanvas) return;
    const ctx = displayCanvas.getContext("2d");

    // Clear
    ctx.clearRect(0, 0, displayCanvas.width, displayCanvas.height);

    if (showMask) {
      // Show mask as red/green overlay
      const maskCanvas = maskCanvasRef.current;
      const maskCtx = maskCanvas.getContext("2d");
      const maskData = maskCtx.getImageData(0, 0, maskCanvas.width, maskCanvas.height);

      // Create colored overlay
      const overlay = ctx.createImageData(maskCanvas.width, maskCanvas.height);
      for (let i = 0; i < maskData.data.length; i += 4) {
        const alpha = maskData.data[i]; // Red channel = alpha value
        // Green for foreground, red for background, yellow for semi-transparent
        if (alpha > 200) {
          // Foreground - green
          overlay.data[i] = 50;
          overlay.data[i + 1] = 255;
          overlay.data[i + 2] = 50;
          overlay.data[i + 3] = 100;
        } else if (alpha < 50) {
          // Background - red
          overlay.data[i] = 255;
          overlay.data[i + 1] = 50;
          overlay.data[i + 2] = 50;
          overlay.data[i + 3] = 100;
        } else {
          // Semi-transparent - yellow
          overlay.data[i] = 255;
          overlay.data[i + 1] = 255;
          overlay.data[i + 2] = 50;
          overlay.data[i + 3] = 150;
        }
      }
      ctx.putImageData(overlay, 0, 0);

      // Draw original image underneath at low opacity
      if (processedImageRef.current) {
        ctx.globalAlpha = 0.3;
        ctx.globalCompositeOperation = "destination-over";
        ctx.drawImage(processedImageRef.current, 0, 0, displayCanvas.width, displayCanvas.height);
        ctx.globalAlpha = 1.0;
        ctx.globalCompositeOperation = "source-over";
      }
    } else {
      // Show processed image with checkerboard
      if (processedImageRef.current) {
        ctx.drawImage(processedImageRef.current, 0, 0, displayCanvas.width, displayCanvas.height);
      }
    }
  }, [showMask]);

  // Re-render when showMask changes
  useEffect(() => {
    renderDisplay();
  }, [showMask, renderDisplay]);

  const getCanvasPos = useCallback((e) => {
    const canvas = displayCanvasRef.current;
    if (!canvas) return null;
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    return {
      x: (e.clientX - rect.left) * scaleX,
      y: (e.clientY - rect.top) * scaleY,
    };
  }, []);

  const applyBrush = useCallback((pos) => {
    const maskCanvas = maskCanvasRef.current;
    const maskCtx = maskCanvas.getContext("2d");
    const displayCanvas = displayCanvasRef.current;
    const displayCtx = displayCanvas.getContext("2d");

    const radius = brushSize;
    const hardnessVal = hardness / 100;
    const opacityVal = opacity / 100;

    // Create radial gradient for soft brush
    const gradient = maskCtx.createRadialGradient(pos.x, pos.y, 0, pos.x, pos.y, radius);
    const innerStop = Math.max(0, hardnessVal - 0.01);

    if (tool === "erase") {
      // Set alpha to 0 (transparent)
      gradient.addColorStop(0, `rgba(0, 0, 0, ${opacityVal})`);
      gradient.addColorStop(innerStop, `rgba(0, 0, 0, ${opacityVal * 0.8})`);
      gradient.addColorStop(1, "rgba(0, 0, 0, 0)");
      maskCtx.globalCompositeOperation = "destination-out";
    } else if (tool === "restore") {
      // Set alpha to 255 (opaque)
      gradient.addColorStop(0, `rgba(255, 255, 255, ${opacityVal})`);
      gradient.addColorStop(innerStop, `rgba(255, 255, 255, ${opacityVal * 0.8})`);
      gradient.addColorStop(1, "rgba(255, 255, 255, 0)");
      maskCtx.globalCompositeOperation = "source-over";
    } else if (tool === "feather") {
      // Blur the mask locally
      const imageData = maskCtx.getImageData(
        Math.max(0, pos.x - radius),
        Math.max(0, pos.y - radius),
        Math.min(maskCanvas.width, radius * 2),
        Math.min(maskCanvas.height, radius * 2)
      );
      // Simple box blur
      const data = imageData.data;
      const blurRadius = Math.max(1, Math.floor(radius / 4));
      for (let i = 0; i < data.length; i += 4) {
        // Average surrounding pixels
        let sum = 0;
        let count = 0;
        const px = (i / 4) % imageData.width;
        const py = Math.floor((i / 4) / imageData.width);
        for (let dy = -blurRadius; dy <= blurRadius; dy++) {
          for (let dx = -blurRadius; dx <= blurRadius; dx++) {
            const nx = px + dx;
            const ny = py + dy;
            if (nx >= 0 && nx < imageData.width && ny >= 0 && ny < imageData.height) {
              const ni = (ny * imageData.width + nx) * 4;
              sum += data[ni];
              count++;
            }
          }
        }
        data[i] = data[i + 1] = data[i + 2] = sum / count;
        data[i + 3] = 255;
      }
      maskCtx.putImageData(imageData, Math.max(0, pos.x - radius), Math.max(0, pos.y - radius));
      maskCtx.globalCompositeOperation = "source-over";
      renderDisplay();
      return;
    }

    maskCtx.fillStyle = gradient;
    maskCtx.beginPath();
    maskCtx.arc(pos.x, pos.y, radius, 0, Math.PI * 2);
    maskCtx.fill();

    // Also draw on display canvas for real-time feedback
    if (!showMask) {
      // Re-render display with updated mask
      renderDisplay();
      // Draw brush indicator
      displayCtx.save();
      displayCtx.strokeStyle = tool === "erase" ? "rgba(255, 60, 60, 0.8)" : "rgba(60, 255, 60, 0.8)";
      displayCtx.lineWidth = 2;
      displayCtx.beginPath();
      displayCtx.arc(pos.x, pos.y, radius, 0, Math.PI * 2);
      displayCtx.stroke();
      displayCtx.restore();
    } else {
      renderDisplay();
    }
  }, [brushSize, hardness, opacity, tool, showMask, renderDisplay]);

  const handleMouseDown = useCallback((e) => {
    setIsDrawing(true);
    const pos = getCanvasPos(e);
    if (pos) {
      lastPosRef.current = pos;
      applyBrush(pos);
    }
  }, [getCanvasPos, applyBrush]);

  const handleMouseMove = useCallback((e) => {
    const pos = getCanvasPos(e);
    if (!pos) return;

    // Draw brush cursor indicator
    if (!isDrawing) {
      const displayCanvas = displayCanvasRef.current;
      const displayCtx = displayCanvas.getContext("2d");
      renderDisplay();
      displayCtx.save();
      displayCtx.strokeStyle = tool === "erase" ? "rgba(255, 60, 60, 0.6)" : tool === "restore" ? "rgba(60, 255, 60, 0.6)" : "rgba(255, 200, 60, 0.6)";
      displayCtx.lineWidth = 1.5;
      displayCtx.setLineDash([4, 4]);
      displayCtx.beginPath();
      displayCtx.arc(pos.x, pos.y, brushSize, 0, Math.PI * 2);
      displayCtx.stroke();
      displayCtx.restore();
      return;
    }

    // Interpolate between last position and current for smooth strokes
    if (lastPosRef.current) {
      const last = lastPosRef.current;
      const dx = pos.x - last.x;
      const dy = pos.y - last.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      const steps = Math.max(1, Math.ceil(dist / (brushSize / 4)));
      for (let i = 1; i <= steps; i++) {
        const t = i / steps;
        applyBrush({ x: last.x + dx * t, y: last.y + dy * t });
      }
    } else {
      applyBrush(pos);
    }
    lastPosRef.current = pos;
  }, [getCanvasPos, isDrawing, brushSize, tool, applyBrush, renderDisplay]);

  const handleMouseUp = useCallback(() => {
    setIsDrawing(false);
    lastPosRef.current = null;
    renderDisplay();
  }, [renderDisplay]);

  const handleMouseLeave = useCallback(() => {
    setIsDrawing(false);
    lastPosRef.current = null;
    renderDisplay();
  }, [renderDisplay]);

  // Touch support
  const handleTouchStart = useCallback((e) => {
    e.preventDefault();
    const touch = e.touches[0];
    handleMouseDown({ clientX: touch.clientX, clientY: touch.clientY });
  }, [handleMouseDown]);

  const handleTouchMove = useCallback((e) => {
    e.preventDefault();
    const touch = e.touches[0];
    handleMouseMove({ clientX: touch.clientX, clientY: touch.clientY });
  }, [handleMouseMove]);

  const handleTouchEnd = useCallback((e) => {
    e.preventDefault();
    handleMouseUp();
  }, [handleMouseUp]);

  const handleApply = useCallback(() => {
    const maskCanvas = maskCanvasRef.current;
    if (!maskCanvas) return;

    // Export mask as PNG blob
    maskCanvas.toBlob((blob) => {
      if (blob && onApply) {
        onApply(blob);
      }
    }, "image/png");
  }, [onApply]);

  const handleReset = useCallback(() => {
    const maskCanvas = maskCanvasRef.current;
    const maskCtx = maskCanvas.getContext("2d");
    if (maskImageRef.current) {
      maskCtx.globalCompositeOperation = "source-over";
      maskCtx.clearRect(0, 0, maskCanvas.width, maskCanvas.height);
      maskCtx.drawImage(maskImageRef.current, 0, 0);
      renderDisplay();
    }
  }, [renderDisplay]);

  const tools = [
    { id: "erase", label: "Erase", icon: eraseIcon, color: "#ff3c3c" },
    { id: "restore", label: "Restore", icon: restoreIcon, color: "#3cff3c" },
    { id: "feather", label: "Feather", icon: featherIcon, color: "#ffc83c" },
  ];

  return (
    <div className="magic-brush-panel">
      <div className="brush-header">
        <div className="flex items-center gap-2.5">
          <div className="brush-header-icon">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9.06 11.9l8.07-8.06a2.85 2.85 0 1 1 4.03 4.03l-8.06 8.08" />
              <path d="M7.07 14.94c-1.66 0-3 1.35-3 3.02 0 1.33-2.5 1.52-2 2.02 1.08 1.1 2.49 2.02 4 2.02 2.2 0 4-1.8 4-4.04a3.01 3.01 0 0 0-3-3.02z" />
            </svg>
          </div>
          <div>
            <p className="text-sm font-semibold text-[var(--color-text-primary)]">Magic Brush</p>
            <p className="text-xs text-[var(--color-text-tertiary)] mt-0.5">Touch up edges manually</p>
          </div>
        </div>
        <button onClick={onCancel} className="brush-close-btn">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>

      <div className="brush-toolbar">
        {tools.map((t) => (
          <button
            key={t.id}
            onClick={() => setTool(t.id)}
            className={`brush-tool-btn ${tool === t.id ? "active" : ""}`}
            style={tool === t.id ? { borderColor: `${t.color}40`, background: `${t.color}15` } : {}}
          >
            <span style={{ color: t.color }}>{t.icon}</span>
            <span>{t.label}</span>
          </button>
        ))}
      </div>

      <div className="brush-controls">
        <label className="brush-control">
          <span className="brush-control-label">Brush Size</span>
          <input
            type="range"
            min="5"
            max="200"
            value={brushSize}
            onChange={(e) => setBrushSize(Number(e.target.value))}
            className="brush-slider"
          />
          <span className="brush-control-value">{brushSize}px</span>
        </label>
        <label className="brush-control">
          <span className="brush-control-label">Hardness</span>
          <input
            type="range"
            min="0"
            max="100"
            value={hardness}
            onChange={(e) => setHardness(Number(e.target.value))}
            className="brush-slider"
          />
          <span className="brush-control-value">{hardness}%</span>
        </label>
        <label className="brush-control">
          <span className="brush-control-label">Opacity</span>
          <input
            type="range"
            min="10"
            max="100"
            value={opacity}
            onChange={(e) => setOpacity(Number(e.target.value))}
            className="brush-slider"
          />
          <span className="brush-control-value">{opacity}%</span>
        </label>
      </div>

      <div className="brush-canvas-container" ref={containerRef}>
        <div className="checkerboard brush-canvas-bg">
          <canvas
            ref={displayCanvasRef}
            className="brush-canvas"
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseLeave}
            onTouchStart={handleTouchStart}
            onTouchMove={handleTouchMove}
            onTouchEnd={handleTouchEnd}
          />
        </div>
        <canvas ref={maskCanvasRef} style={{ display: "none" }} />
      </div>

      <div className="brush-actions">
        <button onClick={() => setShowMask(!showMask)} className="brush-toggle-btn">
          {showMask ? "👁️ Hide Mask" : "👁️ Show Mask"}
        </button>
        <button onClick={handleReset} className="brush-reset-btn">
          ↺ Reset
        </button>
        <div className="flex-1" />
        <button onClick={onCancel} className="brush-cancel-btn">
          Cancel
        </button>
        <button onClick={handleApply} className="brush-apply-btn">
          ✓ Apply Edits
        </button>
      </div>
    </div>
  );
}

// Icons
const eraseIcon = (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M20 20H7L3 16c-1-1-1-3 0-4l9-9c1-1 3-1 4 0l5 5c1 1 1 3 0 4l-7 7" />
    <line x1="18" y1="13" x2="9" y2="4" />
  </svg>
);

const restoreIcon = (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 12a9 9 0 1 0 9-9" />
    <polyline points="3 4 3 10 9 10" />
  </svg>
);

const featherIcon = (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M20.24 12.24a6 6 0 0 0-8.49-8.49L5 10.5V19h8.5z" />
    <line x1="16" y1="8" x2="2" y2="22" />
    <line x1="17.5" y1="15" x2="9" y2="15" />
  </svg>
);