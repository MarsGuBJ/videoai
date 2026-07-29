import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const source = await readFile(new URL('../src/pages/LivePreview/index.tsx', import.meta.url), 'utf8');

test('Live Preview starts stopped cameras only when they are visible', () => {
  assert.match(source, /const startRequestsRef = useRef\(new Set<string>\(\)\)/);
  assert.match(source, /visibleCameras\.filter\(camera => camera\.status !== 'RUNNING'/);
  assert.match(source, /api\.startCamera\(camera\.id\)/);
  assert.match(
    source,
    /setCameras\(current => current\.map\(item => item\.id === started\.id \? started : item\)\)/,
  );
  assert.doesNotMatch(source, /api\.stopCamera/);
});

