function sendChunk(session, blob, offset, total, uploadId, onProgress) {
  return new Promise((resolve, reject) => {
    const form = new FormData();
    form.append("file", blob);
    for (const [key, value] of Object.entries({
      api_key: session.api_key, timestamp: session.timestamp, signature: session.signature,
      public_id: session.public_id, type: session.delivery_type, overwrite: "false",
    })) form.append(key, String(value));
    const request = new XMLHttpRequest();
    request.open("POST", session.upload_url);
    request.setRequestHeader("X-Unique-Upload-Id", uploadId);
    request.setRequestHeader("Content-Range", `bytes ${offset}-${offset + blob.size - 1}/${total}`);
    request.timeout = 120000;
    request.upload.onprogress = (e) => onProgress(Math.round(((offset + e.loaded) / total) * 100));
    request.onerror = () => reject(new Error("Upload connection failed."));
    request.ontimeout = () => reject(new Error("Upload timed out. Try again."));
    request.onload = () => {
      let body; try { body = JSON.parse(request.responseText); } catch { return reject(new Error("Invalid upload response.")); }
      request.status >= 200 && request.status < 300 ? resolve(body) : reject(new Error(body.error?.message || "Cloudinary upload failed."));
    };
    request.send(form);
  });
}

export async function uploadFile(session, file, onProgress) {
  const chunkSize = 10 * 1024 * 1024;
  const uploadId = crypto.randomUUID();
  let result;
  for (let offset = 0; offset < file.size; offset += chunkSize) {
    result = await sendChunk(session, file.slice(offset, offset + chunkSize), offset, file.size, uploadId, onProgress);
  }
  return result;
}

