import type { PersonSearchBboxPoint } from "../api";

export type ImageCropSelection = {
  x: number;
  y: number;
  width: number;
  height: number;
};

// Load the image to resolve its natural size, then convert a percentage crop
// ({x,y,width,height}) into the 4-point pixel bbox polygon the person-search
// API expects. Resolves null when the image cannot be loaded.
export function cropToPixelBbox(imageUrl: string, crop: ImageCropSelection): Promise<PersonSearchBboxPoint[] | null> {
  return new Promise(resolve => {
    const img = new Image();
    img.onload = () => {
      const w = img.naturalWidth;
      const h = img.naturalHeight;
      if (!w || !h) {
        resolve(null);
        return;
      }
      const x1 = Math.round((crop.x / 100) * w);
      const y1 = Math.round((crop.y / 100) * h);
      const x2 = Math.round(((crop.x + crop.width) / 100) * w);
      const y2 = Math.round(((crop.y + crop.height) / 100) * h);
      resolve([
        { x: x1, y: y1 },
        { x: x2, y: y1 },
        { x: x2, y: y2 },
        { x: x1, y: y2 }
      ]);
    };
    img.onerror = () => resolve(null);
    img.src = imageUrl;
  });
}

// Crop a percentage region out of the image via canvas and return it as a new
// File (used to replace the uploaded reference image with the selected region).
// Rejects when the image fails to load, the region is empty, or the canvas is
// tainted (cross-origin image without CORS).
export function cropImageToFile(
  imageUrl: string,
  crop: ImageCropSelection,
  fileName: string,
  mimeType = "image/jpeg"
): Promise<File> {
  const outputType = ["image/jpeg", "image/png", "image/webp"].includes(mimeType) ? mimeType : "image/jpeg";
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      const sx = Math.round((crop.x / 100) * img.naturalWidth);
      const sy = Math.round((crop.y / 100) * img.naturalHeight);
      const sw = Math.round((crop.width / 100) * img.naturalWidth);
      const sh = Math.round((crop.height / 100) * img.naturalHeight);
      if (!sw || !sh) {
        reject(new Error("crop region is empty"));
        return;
      }
      const canvas = document.createElement("canvas");
      canvas.width = sw;
      canvas.height = sh;
      const ctx = canvas.getContext("2d");
      if (!ctx) {
        reject(new Error("canvas 2d context unavailable"));
        return;
      }
      ctx.drawImage(img, sx, sy, sw, sh, 0, 0, sw, sh);
      try {
        canvas.toBlob(
          blob => {
            if (!blob) {
              reject(new Error("canvas toBlob failed"));
              return;
            }
            resolve(new File([blob], fileName, { type: blob.type || outputType }));
          },
          outputType,
          0.92
        );
      } catch (error) {
        reject(error instanceof Error ? error : new Error("canvas export failed"));
      }
    };
    img.onerror = () => reject(new Error("image load failed"));
    img.src = imageUrl;
  });
}
