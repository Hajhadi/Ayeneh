import * as pdfjs from 'pdfjs-dist/legacy/build/pdf.mjs';

const MAX_EXTRACTED_CHARS = 1_500_000;

/** Extract searchable text on-device so document knowledge never needs a server. */
export async function extractDocumentText(file: File): Promise<string> {
  if (file.type === 'text/plain' || file.type === 'text/markdown'
    || /\.(txt|md)$/i.test(file.name)) {
    return file.text();
  }
  if (file.type !== 'application/pdf' && !/\.pdf$/i.test(file.name)) return '';

  const data = new Uint8Array(await file.arrayBuffer());
  // Let the bundler resolve the worker as an app asset; this also works in the
  // Capacitor WebView, where a relative worker URL would otherwise fail.
  pdfjs.GlobalWorkerOptions.workerSrc = new URL(
    'pdfjs-dist/legacy/build/pdf.worker.mjs', import.meta.url,
  ).toString();
  const loadingTask = pdfjs.getDocument({ data, isEvalSupported: false });
  const pdf = await loadingTask.promise;
  const pages: string[] = [];
  try {
    for (let pageNumber = 1; pageNumber <= pdf.numPages; pageNumber += 1) {
      const page = await pdf.getPage(pageNumber);
      const content = await page.getTextContent();
      const text = content.items
        .map((item) => 'str' in item ? pdfjs.normalizeUnicode(item.str).normalize('NFKC') : '')
        .join(' ')
        .replace(/[ \t]+/g, ' ')
        .trim();
      if (text) pages.push(`[Page ${pageNumber}]\n${text}`);
      if (pages.join('\n\n').length >= MAX_EXTRACTED_CHARS) break;
    }
  } finally {
    await pdf.destroy();
  }
  return pages.join('\n\n').slice(0, MAX_EXTRACTED_CHARS);
}
