

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";


export async function removeBackground(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_URL}/api/remove-bg`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    let errorMessage = "Background removal failed";
    try {
      const errorData = await response.json();
      errorMessage = errorData.detail || errorMessage;
    } catch {

    }
    throw new Error(errorMessage);
  }

  const blob = await response.blob();
  const blobUrl = URL.createObjectURL(blob);

  return { blobUrl, blob };
}


export async function checkHealth() {
  try {
    const response = await fetch(`${API_URL}/api/health`);
    return response.ok;
  } catch {
    return false;
  }
}
