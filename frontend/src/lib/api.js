const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

// ---------------------------------------------------------------------------
// Health check
// ---------------------------------------------------------------------------

export async function checkHealth() {
  try {
    const response = await fetch(`${API_URL}/api/health`);
    return response.ok;
  } catch {
    return false;
  }
}

// ---------------------------------------------------------------------------
// Async background removal with SSE progress streaming
// ---------------------------------------------------------------------------

/**
 * Submit a background-removal job and stream progress via SSE.
 *
 * @param {File} file - the image file to process
 * @param {(progress: {stage: string, progress: number, status: string}) => void} onProgress
 * @returns {Promise<{blobUrl: string, blob: Blob, taskId: string}>}
 */
export function removeBackground(file, onProgress) {
  return new Promise((resolve, reject) => {
    const formData = new FormData();
    formData.append("file", file);

    fetch(`${API_URL}/api/remove-bg`, { method: "POST", body: formData })
      .then((res) => {
        if (!res.ok) return res.json().then((d) => Promise.reject(new Error(d.detail || "Submission failed")));
        return res.json();
      })
      .then(({ task_id }) => {
        // Open SSE stream for progress.
        const evtSource = new EventSource(`${API_URL}/api/task/${task_id}/events`);

        evtSource.onmessage = (e) => {
          try {
            const data = JSON.parse(e.data);
            if (onProgress) onProgress(data);
          } catch {}
        };

        evtSource.addEventListener("complete", (e) => {
          evtSource.close();
          try {
            const data = JSON.parse(e.data);
            if (onProgress) onProgress(data);
            if (data.status === "error") {
              reject(new Error(data.error || "Processing failed"));
              return;
            }
          } catch {}

          // Fetch the result image.
          fetch(`${API_URL}/api/task/${task_id}/result`)
            .then((r) => {
              if (!r.ok) return r.json().then((d) => Promise.reject(new Error(d.detail || "Result fetch failed")));
              return r.blob();
            })
            .then((blob) => {
              const blobUrl = URL.createObjectURL(blob);
              resolve({ blobUrl, blob, taskId: task_id });
            })
            .catch(reject);
        });

        evtSource.onerror = () => {
          evtSource.close();
          // Fallback: poll for status.
          pollForResult(task_id, onProgress, resolve, reject);
        };
      })
      .catch(reject);
  });
}

/**
 * Fallback polling if SSE is not supported (e.g., some proxies).
 */
function pollForResult(taskId, onProgress, resolve, reject) {
  const interval = setInterval(async () => {
    try {
      const res = await fetch(`${API_URL}/api/task/${taskId}`);
      if (!res.ok) return;
      const data = await res.json();
      if (onProgress) onProgress(data);

      if (data.status === "done") {
        clearInterval(interval);
        const imgRes = await fetch(`${API_URL}/api/task/${taskId}/result`);
        const blob = await imgRes.blob();
        const blobUrl = URL.createObjectURL(blob);
        resolve({ blobUrl, blob, taskId });
      } else if (data.status === "error") {
        clearInterval(interval);
        reject(new Error(data.error || "Processing failed"));
      }
    } catch (err) {
      clearInterval(interval);
      reject(err);
    }
  }, 500);
}

// ---------------------------------------------------------------------------
// Mask extraction (for the Magic Brush touch-up tool)
// ---------------------------------------------------------------------------

export async function extractMask(file) {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_URL}/api/extract-mask`, { method: "POST", body: formData });
  if (!res.ok) throw new Error("Mask extraction failed");
  const { task_id } = await res.json();

  // Poll until done.
  while (true) {
    await new Promise((r) => setTimeout(r, 400));
    const statusRes = await fetch(`${API_URL}/api/task/${task_id}`);
    const data = await statusRes.json();
    if (data.status === "done") {
      const maskRes = await fetch(`${API_URL}/api/task/${task_id}/mask`);
      const blob = await maskRes.blob();
      return { maskUrl: URL.createObjectURL(blob), maskBlob: blob, taskId: task_id };
    }
    if (data.status === "error") throw new Error(data.error || "Mask extraction failed");
  }
}

// ---------------------------------------------------------------------------
// Composite: apply an edited mask to the original image on the server
// ---------------------------------------------------------------------------

export async function compositeWithMask(file, maskBlob) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("mask", maskBlob, "mask.png");

  const res = await fetch(`${API_URL}/api/composite`, { method: "POST", body: formData });
  if (!res.ok) {
    let msg = "Composite failed";
    try { const d = await res.json(); msg = d.detail || msg; } catch {}
    throw new Error(msg);
  }
  const blob = await res.blob();
  return { blobUrl: URL.createObjectURL(blob), blob };
}
