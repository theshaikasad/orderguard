import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseCatalogue } from '../lib/catalogue.ts';
const bytes = text => new TextEncoder().encode(text);
test('preserves an INR menu exactly',()=>assert.equal(parseCatalogue('menu.txt','text/plain',bytes('Roses ₹699\nRibbon ₹50')),'Roses ₹699\nRibbon ₹50'));
test('rejects unsupported formats and MIME types',()=>{assert.throws(()=>parseCatalogue('menu.pdf','application/pdf',bytes('menu')));assert.throws(()=>parseCatalogue('menu.txt','application/octet-stream',bytes('menu')));});
test('rejects oversized, empty, binary or invalid UTF-8 content',()=>{for(const data of [bytes('x'.repeat(8193)),bytes(' '),bytes('a\0b'),new Uint8Array([255,255])])assert.throws(()=>parseCatalogue('menu.txt','text/plain',data));});
