export function parseCatalogue(name: string, mime: string, bytes: Uint8Array): string {
  if (!name.toLowerCase().endsWith('.txt') || !['', 'text/plain'].includes(mime)) throw new Error('Please upload a plain text (.txt) menu. PDF, images and spreadsheets are not supported.');
  if (bytes.length > 8192) throw new Error('Keep the text menu under 8 KB, or paste a shorter section.');
  let text: string;
  try { text = new TextDecoder('utf-8', { fatal: true }).decode(bytes).replace(/^\uFEFF/, ''); }
  catch { throw new Error('This file is not valid UTF-8 text. Save it as UTF-8 or paste the menu.'); }
  if (!text.trim() || text.length > 8000 || /[\u0000-\u0008\u000B\u000C\u000E-\u001F]/.test(text)) throw new Error('Use a nonempty plain-text menu with at most 8,000 characters.');
  return text;
}
